"""Process-level runtime flags for operational probes (RC1.2)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProcessRuntime:
    """Mutable process flags set during lifespan (not request state)."""

    configuration_validated: bool = False


process_runtime = ProcessRuntime()


def mark_configuration_validated() -> None:
    process_runtime.configuration_validated = True


def reset_process_runtime() -> None:
    """Reset flags (tests / process teardown)."""
    process_runtime.configuration_validated = False


def is_configuration_validated() -> bool:
    return process_runtime.configuration_validated
