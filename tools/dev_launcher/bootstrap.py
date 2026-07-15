"""Alembic + dependency bootstrap helpers."""

from __future__ import annotations

import time
from pathlib import Path

from tools.dev_launcher.console import console
from tools.dev_launcher.processes import run_foreground


def ensure_backend_deps(backend_root: Path) -> None:
    """Ensure the backend virtualenv exists for a fresh clone."""
    venv = backend_root / ".venv"
    if venv.exists():
        console.ok("Backend virtualenv already present")
        return
    console.step("Installing backend dependencies (uv sync)")
    completed = run_foreground(["uv", "sync"], cwd=backend_root, prefix="BACKEND")
    if completed.returncode != 0:
        console.error("uv sync failed")
        raise SystemExit(completed.returncode)
    console.ok("Backend dependencies installed")


def ensure_frontend_deps(frontend_root: Path) -> None:
    node_modules = frontend_root / "node_modules"
    if node_modules.exists():
        console.ok("Frontend node_modules already present")
        return
    console.step("Installing frontend dependencies (npm install)")
    completed = run_foreground(["npm", "install"], cwd=frontend_root, prefix="FRONTEND")
    if completed.returncode != 0:
        console.error("npm install failed")
        raise SystemExit(completed.returncode)
    console.ok("Frontend dependencies installed")


def run_alembic(backend_root: Path) -> float:
    console.step("Running Alembic migrations")
    started = time.perf_counter()
    completed = run_foreground(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=backend_root,
        prefix="BACKEND",
    )
    elapsed = time.perf_counter() - started
    if completed.returncode != 0:
        console.error("Alembic migration failed — full output above")
        if completed.stdout:
            print(completed.stdout)
        if completed.stderr:
            print(completed.stderr)
        raise SystemExit(completed.returncode)
    console.ok(f"Alembic upgrade head succeeded ({elapsed:.1f}s)")
    return elapsed
