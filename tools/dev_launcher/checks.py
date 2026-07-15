"""Tool and repository validation for the developer launcher."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from tools.dev_launcher.console import console
from tools.dev_launcher.executil import resolve_command
from tools.dev_launcher.executil import resolve_command


@dataclass(frozen=True)
class ToolSpec:
    name: str
    command: tuple[str, ...]
    install_hint: str


REQUIRED_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="Python",
        command=("python", "--version"),
        install_hint="Install Python 3.12+ from https://www.python.org/downloads/",
    ),
    ToolSpec(
        name="uv",
        command=("uv", "--version"),
        install_hint="Install uv: https://docs.astral.sh/uv/getting-started/installation/",
    ),
    ToolSpec(
        name="Docker",
        command=("docker", "--version"),
        install_hint="Install Docker Desktop: https://docs.docker.com/get-docker/",
    ),
    ToolSpec(
        name="Docker Compose",
        command=("docker", "compose", "version"),
        install_hint="Install Docker Compose v2 (bundled with Docker Desktop).",
    ),
    ToolSpec(
        name="Node",
        command=("node", "--version"),
        install_hint="Install Node.js 20+ from https://nodejs.org/",
    ),
    ToolSpec(
        name="npm",
        command=("npm", "--version"),
        install_hint="npm ships with Node.js — reinstall Node.js if npm is missing.",
    ),
)

REQUIRED_PATHS: tuple[str, ...] = (
    "backend",
    "frontend",
    "docker-compose.yml",
    ".env",
    "backend/.env",
)


def _run_version(command: tuple[str, ...]) -> tuple[bool, str]:
    resolved = resolve_command(list(command))
    # Prefer a real file path when present; otherwise try launching by name.
    try:
        completed = subprocess.run(
            resolved,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
            shell=False,
        )
    except FileNotFoundError:
        if command[0] == "python":
            for candidate in (("py", "-3", "--version"), ("python3", "--version")):
                alt = resolve_command(list(candidate))
                try:
                    completed = subprocess.run(
                        alt,
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=20,
                        shell=False,
                    )
                except (OSError, subprocess.TimeoutExpired):
                    continue
                output = (completed.stdout or completed.stderr or "").strip()
                if completed.returncode == 0 and output:
                    return True, output.splitlines()[0]
        return False, "not found on PATH"
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    output = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode != 0:
        return False, output or f"exit code {completed.returncode}"
    return True, output.splitlines()[0] if output else "ok"


def validate_tools() -> None:
    console.step("Validating developer tools")
    failures: list[str] = []
    for tool in REQUIRED_TOOLS:
        ok, detail = _run_version(tool.command)
        if ok:
            console.ok(f"{tool.name}: {detail}")
        else:
            console.error(f"{tool.name}: {detail}")
            failures.append(f"- {tool.name}: {tool.install_hint}")
    if failures:
        console.error("Missing required tools:")
        for line in failures:
            console.error(line)
        raise SystemExit(1)


def validate_repository(root: Path) -> None:
    console.step("Validating repository layout")
    missing = [rel for rel in REQUIRED_PATHS if not (root / rel).exists()]
    if missing:
        console.error("Repository is incomplete. Missing:")
        for item in missing:
            console.error(f"  - {item}")
        raise SystemExit(1)
    for item in REQUIRED_PATHS:
        console.ok(f"Found {item}")
