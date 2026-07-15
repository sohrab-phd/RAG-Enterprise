"""Docker Compose helpers."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from tools.dev_launcher.console import console
from tools.dev_launcher.executil import resolve_command

HEALTH_TIMEOUT_SECONDS = 60


class DockerDesktopNotRunningError(RuntimeError):
    """Raised when the Docker engine / Desktop is unavailable."""


def _is_desktop_down(text: str) -> bool:
    lowered = text.lower()
    needles = (
        "docker desktop is not running",
        "cannot connect to the docker daemon",
        "error during connect",
        "the system cannot find the file specified",
        "open //./pipe/dockerdesktop",
        "is the docker daemon running",
        "failed to connect",
    )
    return any(item in lowered for item in needles)


def run_compose(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = resolve_command(["docker", "compose", *args])
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
    except FileNotFoundError as exc:
        raise DockerDesktopNotRunningError("Docker is not installed or not on PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"docker compose timed out: {' '.join(args)}") from exc

    combined = f"{completed.stdout}\n{completed.stderr}".strip()
    if completed.returncode != 0 and _is_desktop_down(combined):
        raise DockerDesktopNotRunningError("Docker Desktop is not running.")
    if check and completed.returncode != 0:
        raise RuntimeError(combined or f"docker compose failed ({completed.returncode})")
    return completed


def ensure_docker_engine() -> None:
    console.step("Checking Docker engine")
    try:
        completed = subprocess.run(
            resolve_command(["docker", "info"]),
            capture_output=True,
            text=True,
            check=False,
            timeout=40,
        )
    except FileNotFoundError as exc:
        raise DockerDesktopNotRunningError("Docker is not installed or not on PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise DockerDesktopNotRunningError("Docker Desktop is not running.") from exc
    combined = f"{completed.stdout}\n{completed.stderr}"
    if completed.returncode != 0 or _is_desktop_down(combined):
        raise DockerDesktopNotRunningError("Docker Desktop is not running.")
    console.ok("Docker engine is reachable")


def compose_up(root: Path) -> float:
    """Start compose services without unnecessary recreates. Returns elapsed seconds."""
    console.step("Starting Docker Compose services")
    started = time.perf_counter()
    # --no-recreate keeps healthy existing containers.
    completed = run_compose(root, "up", "-d", "--no-recreate", check=False)
    if completed.returncode != 0:
        # Fallback when flags differ across compose versions.
        completed = run_compose(root, "up", "-d", check=True)
    for line in (completed.stdout or "").splitlines():
        if line.strip():
            console.process("DOCKER", line)
    for line in (completed.stderr or "").splitlines():
        if line.strip():
            console.process("DOCKER", line)
    elapsed = time.perf_counter() - started
    console.ok(f"Docker Compose up complete ({elapsed:.1f}s)")
    return elapsed


def _service_health(root: Path, service: str) -> str:
    completed = run_compose(root, "ps", "--format", "json", service, check=False)
    if completed.returncode != 0:
        return "unknown"
    raw = (completed.stdout or "").strip()
    if not raw:
        return "missing"
    # Compose may emit one JSON object per line or a JSON array.
    payloads: list[dict[str, object]] = []
    if raw.startswith("["):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                payloads = [item for item in data if isinstance(item, dict)]
        except json.JSONDecodeError:
            return "unknown"
    else:
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                payloads.append(item)
    if not payloads:
        return "missing"
    health = str(payloads[0].get("Health") or "").lower()
    state = str(payloads[0].get("State") or payloads[0].get("Status") or "").lower()
    if health == "healthy":
        return "healthy"
    if "health: starting" in state or health == "starting":
        return "starting"
    if "running" in state and not health:
        return "running"
    return health or state or "unknown"


def wait_for_healthy_services(root: Path, *, timeout: int = HEALTH_TIMEOUT_SECONDS) -> float:
    console.step("Waiting for Docker health checks")
    started = time.perf_counter()
    deadline = started + timeout
    postgres_ok = False
    redis_ok = False
    while time.perf_counter() < deadline:
        if not postgres_ok:
            status = _service_health(root, "postgres")
            console.info(f"Waiting for PostgreSQL... ({status})")
            if status == "healthy":
                postgres_ok = True
                console.ok("PostgreSQL is healthy")
        if not redis_ok:
            status = _service_health(root, "redis")
            console.info(f"Waiting for Redis... ({status})")
            if status == "healthy":
                redis_ok = True
                console.ok("Redis is healthy")
        if postgres_ok and redis_ok:
            return time.perf_counter() - started
        time.sleep(2.0)
    missing = []
    if not postgres_ok:
        missing.append("PostgreSQL")
    if not redis_ok:
        missing.append("Redis")
    raise RuntimeError(
        f"Timed out after {timeout}s waiting for healthy services: {', '.join(missing)}"
    )


def compose_down(root: Path) -> None:
    console.step("Stopping Docker Compose services (preserving volumes)")
    completed = run_compose(root, "down", check=False)
    for line in (completed.stdout or "").splitlines():
        if line.strip():
            console.process("DOCKER", line)
    for line in (completed.stderr or "").splitlines():
        if line.strip():
            console.process("DOCKER", line)
    if completed.returncode == 0:
        console.ok("docker compose down complete")
    else:
        console.warning("docker compose down returned a non-zero exit code")
