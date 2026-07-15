"""Port occupancy helpers."""

from __future__ import annotations

import socket
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request, urlopen

from tools.dev_launcher.console import console


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
        console.info(f"Frontend port {frontend_port}: free")
    elif frontend.reusable:
        console.ok(f"Frontend port {frontend_port}: {frontend.detail}")
        reuse_frontend = True
    else:
        console.error(frontend.detail)
        console.error("Stop the other process or free port 5173, then retry.")
        raise SystemExit(1)

    return reuse_backend, reuse_frontend
