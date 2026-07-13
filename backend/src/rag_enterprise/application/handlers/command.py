"""Command handler abstractions."""

from __future__ import annotations

from typing import Protocol, TypeVar

from rag_enterprise.application.commands.base import Command
from rag_enterprise.application.common import Result

C = TypeVar("C", bound=Command, contravariant=True)
R = TypeVar("R")


class CommandHandler(Protocol[C, R]):
    """Handle a command and return a typed Result."""

    async def handle(self, command: C) -> Result[R]:
        """Execute the command."""
