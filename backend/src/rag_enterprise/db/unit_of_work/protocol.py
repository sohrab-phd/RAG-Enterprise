"""Unit of Work protocol."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from sqlalchemy.ext.asyncio import AsyncSession


class UnitOfWorkProtocol(Protocol):
    """Transaction boundary abstraction."""

    @property
    def session(self) -> AsyncSession:
        """Return the active database session."""

    async def commit(self) -> None:
        """Commit the current transaction."""

    async def rollback(self) -> None:
        """Roll back the current transaction."""

    async def __aenter__(self) -> Self:
        """Enter the unit-of-work context."""

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Exit the unit-of-work context."""
