"""End-to-end verification for the developer launcher (start + graceful stop)."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]


def _http_status(url: str, timeout: float = 5.0) -> int | None:
    try:
        with urlopen(Request(url, method="GET"), timeout=timeout) as response:  # noqa: S310
            return int(getattr(response, "status", 200) or 200)
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    env = os.environ.copy()
    env["AUTO_OPEN_BROWSER"] = "false"
    env["PYTHONUTF8"] = "1"
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    print("[VERIFY] starting run.py")
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "run.py")],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    assert proc.stdout is not None
    ready = False
    deadline = time.perf_counter() + 420

    def _drain() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line.rstrip())

    # After the ready banner we keep draining stdout in a thread so the child
    # cannot deadlock on a full pipe.
    import threading

    while time.perf_counter() < deadline:
        line = proc.stdout.readline()
        if line:
            print(line.rstrip())
            if "RAG-enterprise is ready" in line:
                ready = True
                break
        elif proc.poll() is not None:
            print("[VERIFY] launcher exited early")
            return 1
    if not ready:
        print("[VERIFY] timed out waiting for ready banner")
        proc.kill()
        return 1

    drainer = threading.Thread(target=_drain, daemon=True)
    drainer.start()

    # Drain a bit more while checking endpoints.
    time.sleep(2)
    checks = {
        "ready": _http_status("http://127.0.0.1:8000/api/v1/ready", timeout=60),
        "docs": _http_status("http://127.0.0.1:8000/docs", timeout=15),
        "frontend": _http_status("http://127.0.0.1:5173/", timeout=15),
        "system": _http_status("http://127.0.0.1:8000/api/v1/system", timeout=30),
    }
    print(f"[VERIFY] http checks: {checks}")
    if checks["ready"] != 200 or checks["frontend"] != 200 or checks["docs"] != 200:
        print("[VERIFY] endpoint checks failed")
        _stop(proc)
        return 1

    print("[VERIFY] sending graceful stop signal (.dev_launcher_stop)")
    stop_file = ROOT / ".dev_launcher_stop"
    stop_file.write_text("stop\n", encoding="utf-8")
    try:
        code = proc.wait(timeout=180)
    except subprocess.TimeoutExpired:
        print("[VERIFY] stop timed out; forcing process tree kill")
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            proc.kill()
        code = proc.wait(timeout=60)
        # Best-effort compose down if launcher never reached cleanup.
        subprocess.run(
            ["docker", "compose", "down"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    print(f"[VERIFY] launcher exit code: {code}")
    stop_file.unlink(missing_ok=True)

    time.sleep(3)
    after = {
        "ready": _http_status("http://127.0.0.1:8000/api/v1/ready", timeout=2),
        "frontend": _http_status("http://127.0.0.1:5173/", timeout=2),
    }
    compose = subprocess.run(
        ["docker", "compose", "ps", "--status", "running", "--format", "{{.Name}}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    running = [line.strip() for line in (compose.stdout or "").splitlines() if line.strip()]
    print(f"[VERIFY] after stop http={after} docker_running={running}")
    if after["ready"] is not None or after["frontend"] is not None:
        print("[VERIFY] FAIL: app ports still responding")
        return 1
    if running:
        print("[VERIFY] FAIL: docker services still running")
        return 1
    print("[VERIFY] SUCCESS")
    return 0


def _stop(proc: subprocess.Popen[str]) -> None:
    try:
        if sys.platform == "win32":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.send_signal(signal.SIGINT)
    except OSError:
        proc.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
