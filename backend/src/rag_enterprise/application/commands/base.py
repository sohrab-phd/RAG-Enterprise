"""Command abstractions."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from rag_enterprise.application.common import ApplicationError, ErrorCode, Result


@runtime_checkable
class Command(Protocol):
    """Marker protocol for write-side application commands."""

    async def validate_command(self) -> Result[None]:
        """Validate command invariants before handling."""


class CommandBase(BaseModel):
    """Base class for commands with a validation hook."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    async def validate_command(self) -> Result[None]:
        """Override to add command-specific validation."""
        return Result.ok(None)

    def validation_error(self, message: str, **details: object) -> Result[None]:
        """Helper for returning a validation failure."""
        return Result.fail(
            ApplicationError(
                code=ErrorCode.VALIDATION_FAILED,
                message=message,
                details={key: value for key, value in details.items()},
            )
        )
