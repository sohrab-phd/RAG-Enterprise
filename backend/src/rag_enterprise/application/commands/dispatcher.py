"""Command dispatcher."""

from __future__ import annotations

from typing import TypeVar, cast

from rag_enterprise.application.commands.base import Command
from rag_enterprise.application.common import ApplicationError, ErrorCode, Result
from rag_enterprise.application.handlers.command import CommandHandler

C = TypeVar("C", bound=Command)
R = TypeVar("R")


class CommandDispatcher:
    """Lightweight in-process command dispatcher."""

    def __init__(self) -> None:
        self._handlers: dict[type[Command], CommandHandler[Command, object]] = {}

    def register(self, command_type: type[C], handler: CommandHandler[C, R]) -> None:
        """Register a handler for a command type."""
        if command_type in self._handlers:
            raise ValueError(f"Handler already registered for {command_type.__name__}")
        self._handlers[command_type] = handler  # type: ignore[assignment]

    def is_registered(self, command_type: type[Command]) -> bool:
        """Return whether a handler is registered for the command type."""
        return command_type in self._handlers

    async def dispatch(self, command: C) -> Result[R]:
        """Validate and dispatch a command to its handler."""
        handler = self._handlers.get(type(command))
        if handler is None:
            return Result.fail(
                ApplicationError(
                    code=ErrorCode.HANDLER_NOT_FOUND,
                    message=f"No handler registered for {type(command).__name__}",
                )
            )

        validation = await command.validate_command()
        if validation.is_failure:
            if validation.error is None:
                return Result.fail(
                    ApplicationError(
                        code=ErrorCode.VALIDATION_FAILED,
                        message="Command validation failed",
                    )
                )
            return Result.fail(validation.error)

        return cast(Result[R], await handler.handle(command))
