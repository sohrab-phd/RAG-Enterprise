"""Port occupancy helpers."""

from __future__ import annotations

import socket
import subprocess
import sys
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request, urlopen

from tools.dev_launcher.console import console

# Prefer ports outside common Hyper-V / WinNAT exclusion blocks.
_CANDIDATE_PORTS = (8300, 8500, 8800, 9000, 9100, 9200, 18000)


@dataclass(frozen=True)
class PortCheck:
    port: int
    label: str
    reusable: bool
    detail: str


def is_port_open(host: str, port: int, *, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def can_bind_port(port: int, *, host: str = "0.0.0.0") -> bool:
    """Return True if this process can bind TCP ``host:port`` (listen readiness)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def windows_excluded_tcp_ranges() -> list[tuple[int, int]]:
    """Parse ``netsh`` TCP exclusion ranges (Hyper-V / WinNAT). Empty on non-Windows."""
    if sys.platform != "win32":
        return []
    try:
        completed = subprocess.run(
            ["netsh", "interface", "ipv4", "show", "excludedportrange", "protocol=tcp"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    ranges: list[tuple[int, int]] = []
    for line in (completed.stdout or "").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            start = int(parts[0])
            end = int(parts[1])
        except ValueError:
            continue
        if 0 < start <= end <= 65535:
            ranges.append((start, end))
    return ranges


def port_in_ranges(port: int, ranges: list[tuple[int, int]]) -> tuple[int, int] | None:
    for start, end in ranges:
        if start <= port <= end:
            return start, end
    return None


def suggest_bindable_port(*, avoid: int) -> int | None:
    for candidate in _CANDIDATE_PORTS:
        if candidate == avoid:
            continue
        if can_bind_port(candidate):
            return candidate
    return None


def _http_ok(url: str, *, timeout: float = 2.0) -> tuple[bool, int | None]:
    try:
        with urlopen(Request(url, method="GET"), timeout=timeout) as response:  # noqa: S310
            return True, int(getattr(response, "status", 200) or 200)
    except URLError:
        return False, None
    except OSError:
        return False, None


def check_backend_reusable(host: str, port: int) -> PortCheck:
    if not is_port_open(host, port):
        return PortCheck(port, "backend", False, "free")
    live_ok, _ = _http_ok(f"http://{host}:{port}/api/v1/live")
    if live_ok:
        return PortCheck(port, "backend", True, "RAG-enterprise backend already responding")
    return PortCheck(
        port,
        "backend",
        False,
        f"port {port} is occupied by another process (not /api/v1/live)",
    )


def check_frontend_reusable(host: str, port: int) -> PortCheck:
    if not is_port_open(host, port):
        return PortCheck(port, "frontend", False, "free")
    ok, status = _http_ok(f"http://{host}:{port}/")
    if ok and status is not None and status < 500:
        return PortCheck(port, "frontend", True, "HTTP service already responding on Vite port")
    return PortCheck(
        port,
        "frontend",
        False,
        f"port {port} is occupied by another process",
    )


def _fail_unbindable(label: str, port: int) -> None:
    excluded = port_in_ranges(port, windows_excluded_tcp_ranges())
    suggested = suggest_bindable_port(avoid=port)
    console.error(f"{label} port {port} cannot be bound (WinError 10013 / access denied).")
    if excluded is not None:
        start, end = excluded
        console.error(
            f"Port {port} is inside a Windows excluded TCP range ({start}-{end}), "
            "often reserved by Hyper-V / WinNAT."
        )
    if suggested is not None:
        console.error(
            f"Set BACKEND_PORT={suggested} and VITE_API_BASE_URL=http://localhost:{suggested} "
            "in backend/.env (and root .env if present), then retry."
        )
    else:
        console.error("Choose another BACKEND_PORT outside Windows excluded ranges, then retry.")
    raise SystemExit(1)


def report_ports(
    *,
    postgres_port: int,
    redis_port: int,
    backend_port: int,
    frontend_port: int,
) -> tuple[bool, bool]:
    """Return (reuse_backend, reuse_frontend). Exits if critical foreign occupancy."""
    console.step("Checking ports")
    reuse_backend = False
    reuse_frontend = False

    for port, label in (
        (postgres_port, "PostgreSQL"),
        (redis_port, "Redis"),
    ):
        if is_port_open("127.0.0.1", port):
            console.info(f"{label} port {port}: in use (will reuse if Docker service)")
        else:
            console.info(f"{label} port {port}: free")

    backend = check_backend_reusable("127.0.0.1", backend_port)
    if backend.detail == "free":
        if not can_bind_port(backend_port):
            _fail_unbindable("Backend", backend_port)
        console.info(f"Backend port {backend_port}: free")
    elif backend.reusable:
        console.ok(f"Backend port {backend_port}: {backend.detail}")
        reuse_backend = True
    else:
        console.error(backend.detail)
        console.error("Stop the other process or change BACKEND_PORT, then retry.")
        raise SystemExit(1)

    frontend = check_frontend_reusable("127.0.0.1", frontend_port)
    if frontend.detail == "free":
        if not can_bind_port(frontend_port):
            console.error(f"Frontend port {frontend_port} cannot be bound.")
            raise SystemExit(1)
        console.info(f"Frontend port {frontend_port}: free")
    elif frontend.reusable:
        console.ok(f"Frontend port {frontend_port}: {frontend.detail}")
        reuse_frontend = True
    else:
        console.error(frontend.detail)
        console.error("Stop the other process or free port 5173, then retry.")
        raise SystemExit(1)

    return reuse_backend, reuse_frontend
