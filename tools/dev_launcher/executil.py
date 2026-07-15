"""Cross-platform executable resolution (Windows .cmd/.bat support)."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def resolve_command(command: list[str]) -> list[str]:
    """Resolve the executable path so Windows can run npm/uv/docker scripts."""
    if not command:
        return command
    name = command[0]
    if Path(name).is_file():
        return command

    found = shutil.which(name)
    if found:
        return [found, *command[1:]]

    if sys.platform == "win32":
        for suffix in (".cmd", ".bat", ".exe"):
            candidate = shutil.which(f"{name}{suffix}")
            if candidate:
                return [candidate, *command[1:]]
        # Node installers sometimes put npm.cmd next to node.exe.
        node = shutil.which("node") or shutil.which("node.exe")
        if node and name == "npm":
            sibling = Path(node).with_name("npm.cmd")
            if sibling.exists():
                return [str(sibling), *command[1:]]

    # Last resort: keep original (may still fail with a clear message).
    return command


def which_or_hint(name: str) -> str | None:
    resolved = resolve_command([name])
    if resolved and Path(resolved[0]).exists():
        return resolved[0]
    return shutil.which(name)
