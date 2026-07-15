"""Orchestrate the full local development stack."""

from __future__ import annotations

import atexit
import os
import re
import signal
import sys
import time
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tools.dev_launcher.bootstrap import (
    ensure_backend_deps,
    ensure_frontend_deps,
    run_alembic,
)
from tools.dev_launcher.checks import validate_repository, validate_tools
from tools.dev_launcher.console import console
from tools.dev_launcher.docker import (
    DockerDesktopNotRunningError,
    compose_down,
    compose_up,
    ensure_docker_engine,
    wait_for_healthy_services,
)
from tools.dev_launcher.ports import report_ports
from tools.dev_launcher.processes import ManagedProcess, spawn

_VITE_LOCAL_RE = re.compile(
    r"Local:\s*(https?://[^\s]+)",
    re.IGNORECASE,
)


@dataclass
class Timing:
    docker: float = 0.0
    docker_health: float = 0.0
    migration: float = 0.0
    backend: float = 0.0
    frontend: float = 0.0
    total: float = 0.0


@dataclass
class LauncherState:
    root: Path
    backend: ManagedProcess | None = None
    frontend: ManagedProcess | None = None
    reuse_backend: bool = False
    reuse_frontend: bool = False
    frontend_url: str | None = None
    shutting_down: bool = False
    timing: Timing = field(default_factory=Timing)


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _read_dotenv_value(path: Path, key: str, default: str) -> str:
    if not path.exists():
        return default
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, _, value = stripped.partition("=")
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return default


def _wait_http_ready(url: str, *, timeout: float, label: str) -> float:
    console.step(f"Waiting for {label}")
    started = time.perf_counter()
    deadline = started + timeout
    last_status = "…"
    while time.perf_counter() < deadline:
        try:
            with urlopen(Request(url, method="GET"), timeout=5) as response:  # noqa: S310
                status = int(getattr(response, "status", 200) or 200)
                if status == 200:
                    elapsed = time.perf_counter() - started
                    console.ok(f"{label} ready ({elapsed:.1f}s)")
                    return elapsed
                last_status = str(status)
        except HTTPError as exc:
            last_status = str(exc.code)
        except (URLError, OSError, TimeoutError) as exc:
            last_status = type(exc).__name__
        console.info(f"Waiting for {label}... ({last_status})")
        time.sleep(2.0)
    raise RuntimeError(f"Timed out waiting for {label} at {url}")


def _extract_vite_url(lines: list[str], fallback: str) -> str:
    for line in reversed(lines):
        match = _VITE_LOCAL_RE.search(line)
        if match:
            return match.group(1).rstrip("/")
    return fallback


def _wait_for_vite_url(proc: ManagedProcess, *, timeout: float, fallback: str) -> tuple[str, float]:
    console.step("Detecting frontend URL from Vite output")
    started = time.perf_counter()
    deadline = started + timeout
    while time.perf_counter() < deadline:
        url = _extract_vite_url(proc.captured_lines, "")
        if url:
            elapsed = time.perf_counter() - started
            console.ok(f"Frontend URL: {url} ({elapsed:.1f}s)")
            return url, elapsed
        if proc.poll() is not None:
            raise RuntimeError("Frontend process exited before printing Local URL")
        console.info("Waiting for Vite Local URL...")
        time.sleep(1.0)
    console.warning(f"Vite Local URL not detected; falling back to {fallback}")
    return fallback, time.perf_counter() - started


def _shutdown(state: LauncherState) -> None:
    if state.shutting_down:
        return
    state.shutting_down = True
    console.banner("Shutting down RAG-enterprise development stack")
    if state.frontend is not None and not state.reuse_frontend:
        state.frontend.terminate()
    elif state.reuse_frontend:
        console.info("Leaving reused frontend process running")
    if state.backend is not None and not state.reuse_backend:
        state.backend.terminate()
    elif state.reuse_backend:
        console.info("Leaving reused backend process running")
    try:
        compose_down(state.root)
    except Exception as exc:  # noqa: BLE001 — best-effort shutdown path
        console.warning(f"docker compose down issue: {exc}")
    console.ok("Shutdown complete")


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    # Prefer repo-root imports when launched via `uv run python run.py`.
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    state = LauncherState(root=root)
    total_started = time.perf_counter()

    def _handle_signal(_signum: int, _frame: object | None) -> None:
        _shutdown(state)
        raise SystemExit(0)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle_signal)
        except (ValueError, OSError):
            pass
    if sys.platform == "win32" and hasattr(signal, "SIGBREAK"):
        try:
            signal.signal(signal.SIGBREAK, _handle_signal)
        except (ValueError, OSError):
            pass
    atexit.register(lambda: _shutdown(state))

    console.banner("RAG-enterprise developer launcher")

    validate_tools()
    validate_repository(root)

    root_env = root / ".env"
    backend_env = root / "backend" / ".env"
    postgres_port = int(_read_dotenv_value(root_env, "POSTGRES_PORT", "5432"))
    redis_port = int(_read_dotenv_value(root_env, "REDIS_PORT", "6379"))
    backend_port = int(_read_dotenv_value(backend_env, "BACKEND_PORT", "8000"))
    frontend_port = 5173
    auto_open = _env_bool("AUTO_OPEN_BROWSER", True)

    reuse_backend, reuse_frontend = report_ports(
        postgres_port=postgres_port,
        redis_port=redis_port,
        backend_port=backend_port,
        frontend_port=frontend_port,
    )
    state.reuse_backend = reuse_backend
    state.reuse_frontend = reuse_frontend

    try:
        ensure_docker_engine()
        state.timing.docker = compose_up(root)
        state.timing.docker_health = wait_for_healthy_services(root)
    except DockerDesktopNotRunningError as exc:
        console.error(str(exc))
        console.error("Start Docker Desktop, wait until it is ready, then re-run:")
        console.error("  uv run python run.py")
        return 1
    except Exception as exc:  # noqa: BLE001
        console.error(f"Docker startup failed: {exc}")
        return 1

    backend_root = root / "backend"
    frontend_root = root / "frontend"
    ensure_backend_deps(backend_root)
    ensure_frontend_deps(frontend_root)

    try:
        state.timing.migration = run_alembic(backend_root)
    except SystemExit as exc:
        return int(exc.code or 1)

    backend_url = f"http://127.0.0.1:{backend_port}"
    if reuse_backend:
        console.ok(f"Reusing existing backend at {backend_url}")
        state.timing.backend = _wait_http_ready(
            f"{backend_url}/api/v1/ready",
            timeout=120,
            label="backend /ready (reused)",
        )
    else:
        console.step("Starting backend (uvicorn --reload)")
        backend_started = time.perf_counter()
        state.backend = spawn(
            "BACKEND",
            [
                "uv",
                "run",
                "uvicorn",
                "rag_enterprise.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                str(backend_port),
                "--reload",
            ],
            cwd=backend_root,
        )
        # First boot may load embeddings + probe Ollama.
        try:
            _wait_http_ready(
                f"{backend_url}/api/v1/ready",
                timeout=300,
                label="backend /ready",
            )
        except Exception:
            if state.backend.poll() is not None:
                console.error("Backend process exited before becoming ready")
            _shutdown(state)
            raise
        state.timing.backend = time.perf_counter() - backend_started

    fallback_frontend = f"http://localhost:{frontend_port}"
    if reuse_frontend:
        console.ok(f"Reusing existing frontend at {fallback_frontend}")
        state.frontend_url = fallback_frontend
        state.timing.frontend = 0.0
    else:
        console.step("Starting frontend (npm run dev)")
        frontend_started = time.perf_counter()
        state.frontend = spawn(
            "FRONTEND",
            ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(frontend_port)],
            cwd=frontend_root,
        )
        try:
            url, _ = _wait_for_vite_url(
                state.frontend,
                timeout=120,
                fallback=fallback_frontend,
            )
            state.frontend_url = url
            # Also confirm HTTP responds.
            _wait_http_ready(url, timeout=60, label="frontend HTTP")
        except Exception:
            _shutdown(state)
            raise
        state.timing.frontend = time.perf_counter() - frontend_started

    state.timing.total = time.perf_counter() - total_started
    frontend_url = state.frontend_url or fallback_frontend

    console.banner(
        "RAG-enterprise is ready.\n\n"
        f"Frontend\n{frontend_url}\n\n"
        f"Swagger\n{backend_url}/docs\n\n"
        f"Health\n{backend_url}/api/v1/ready\n\n"
        f"System\n{backend_url}/api/v1/system\n\n"
        "Startup times\n"
        f"  Docker:     {state.timing.docker:.1f}s\n"
        f"  Health:     {state.timing.docker_health:.1f}s\n"
        f"  Migration:  {state.timing.migration:.1f}s\n"
        f"  Backend:    {state.timing.backend:.1f}s\n"
        f"  Frontend:   {state.timing.frontend:.1f}s\n"
        f"  Total:      {state.timing.total:.1f}s\n\n"
        "Press CTRL+C to stop everything."
    )

    if auto_open:
        console.info(f"Opening browser ({frontend_url})")
        try:
            webbrowser.open(frontend_url)
        except Exception as exc:  # noqa: BLE001
            console.warning(f"Could not open browser: {exc}")
    else:
        console.info("AUTO_OPEN_BROWSER is disabled")

    # Keep process alive while children run.
    stop_file = root / ".dev_launcher_stop"
    if stop_file.exists():
        stop_file.unlink(missing_ok=True)
    try:
        while True:
            if stop_file.exists():
                console.info("Stop signal received (.dev_launcher_stop)")
                stop_file.unlink(missing_ok=True)
                break
            if state.backend is not None and state.backend.poll() is not None:
                console.error("Backend exited unexpectedly")
                break
            if state.frontend is not None and state.frontend.poll() is not None:
                console.error("Frontend exited unexpectedly")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        _shutdown(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
