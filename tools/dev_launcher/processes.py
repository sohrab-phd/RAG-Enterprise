"""Background process helpers with prefixed logs."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from tools.dev_launcher.console import console
from tools.dev_launcher.executil import resolve_command


@dataclass
class ManagedProcess:
    name: str
    process: subprocess.Popen[str]
    _stop_reader: threading.Event = field(default_factory=threading.Event)
    _reader: threading.Thread | None = None
    captured_lines: list[str] = field(default_factory=list)

    def start_log_pump(self) -> None:
        def _pump() -> None:
            assert self.process.stdout is not None
            for line in self.process.stdout:
                if self._stop_reader.is_set():
                    break
                text = line.rstrip("\n")
                self.captured_lines.append(text)
                # Keep a bounded buffer for URL detection.
                if len(self.captured_lines) > 4000:
                    self.captured_lines = self.captured_lines[-2000:]
                console.process(self.name, text)

        self._reader = threading.Thread(target=_pump, name=f"{self.name}-log", daemon=True)
        self._reader.start()

    def poll(self) -> int | None:
        return self.process.poll()

    def terminate(self, *, grace_seconds: float = 8.0) -> None:
        if self.process.poll() is not None:
            self._stop_reader.set()
            return
        console.info(f"Stopping {self.name} (pid={self.process.pid})")
        try:
            if sys.platform == "win32":
                # First try polite break to the process group created at spawn.
                try:
                    self.process.send_signal(signal.CTRL_BREAK_EVENT)
                except OSError:
                    self.process.terminate()
            else:
                self.process.send_signal(signal.SIGTERM)
        except OSError:
            try:
                self.process.terminate()
            except OSError:
                pass
        deadline = time.perf_counter() + grace_seconds
        while time.perf_counter() < deadline:
            if self.process.poll() is not None:
                break
            time.sleep(0.2)
        if self.process.poll() is None:
            console.warning(f"{self.name} did not exit gracefully; killing process tree")
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                    capture_output=True,
                    check=False,
                )
            else:
                try:
                    self.process.kill()
                except OSError:
                    pass
        # Windows cmd.exe wrappers (npm.cmd) often sit on "Terminate batch job (Y/N)?" —
        # force the tree even after a "successful" signal return if still alive.
        if sys.platform == "win32" and self.process.poll() is None:
            subprocess.run(
                ["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        # Extra sweep for vite/uvicorn children whose parent already exited.
        if sys.platform == "win32":
            time.sleep(0.3)
        self._stop_reader.set()
        if self._reader is not None:
            self._reader.join(timeout=2.0)


def spawn(
    name: str,
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> ManagedProcess:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    # Force UTF-8 so Persian / Vite unicode logs do not crash the console reader.
    merged.setdefault("PYTHONUTF8", "1")
    merged.setdefault("PYTHONIOENCODING", "utf-8")

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    process = subprocess.Popen(
        resolve_command(command),
        cwd=cwd,
        env=merged,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=creationflags,
    )
    managed = ManagedProcess(name=name, process=process)
    managed.start_log_pump()
    return managed


def run_foreground(
    command: list[str],
    *,
    cwd: Path,
    prefix: str,
    on_output: Callable[[str], None] | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        resolve_command(command),
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    for stream in (completed.stdout or "", completed.stderr or ""):
        for line in stream.splitlines():
            console.process(prefix, line)
            if on_output is not None:
                on_output(line)
    return completed
