"""Clock interface."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Provides testable access to the current time."""

    def now(self) -> datetime:
        """Return the current UTC timestamp."""
