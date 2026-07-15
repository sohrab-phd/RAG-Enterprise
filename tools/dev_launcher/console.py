"""Colored console helpers for the developer launcher."""

from __future__ import annotations

import os
import sys
from typing import TextIO


def _supports_color(stream: TextIO) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(stream, "isatty") and stream.isatty()


class Console:
    """Lightweight tagged logger with optional ANSI colors."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream or sys.stdout
        self._color = _supports_color(self._stream)

    def _paint(self, color: str, text: str) -> str:
        if not self._color:
            return text
        return f"{color}{text}{self.RESET}"

    def _write(self, tag: str, tag_color: str, message: str) -> None:
        prefix = self._paint(tag_color + self.BOLD, f"[{tag}]")
        self._stream.write(f"{prefix} {message}\n")
        self._stream.flush()

    def info(self, message: str) -> None:
        self._write("INFO", self.CYAN, message)

    def ok(self, message: str) -> None:
        self._write("OK", self.GREEN, message)

    def warning(self, message: str) -> None:
        self._write("WARNING", self.YELLOW, message)

    def error(self, message: str) -> None:
        self._write("ERROR", self.RED, message)

    def step(self, message: str) -> None:
        self._write("STEP", self.BLUE, message)

    def banner(self, message: str) -> None:
        line = "=" * 51
        self._stream.write(f"\n{self._paint(self.BOLD, line)}\n")
        self._stream.write(f"{message}\n")
        self._stream.write(f"{self._paint(self.BOLD, line)}\n\n")
        self._stream.flush()

    def process(self, name: str, line: str) -> None:
        color = {
            "BACKEND": self.MAGENTA,
            "FRONTEND": self.CYAN,
            "DOCKER": self.BLUE,
        }.get(name.upper(), self.DIM)
        prefix = self._paint(color + self.BOLD, f"[{name.upper()}]")
        # Prefer stderr for high-volume process logs so piped stdout (verification /
        # CI) cannot fill and deadlock the wait loop.
        stream = sys.stderr if not self._stream.isatty() else self._stream
        try:
            stream.write(f"{prefix} {line.rstrip()}\n")
            stream.flush()
        except OSError:
            pass


console = Console()
