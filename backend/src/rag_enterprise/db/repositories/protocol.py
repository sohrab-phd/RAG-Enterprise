"""Repository protocol."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Protocol, TypeVar

T = TypeVar("T")


class RepositoryProtocol(Protocol[T]):
    """Generic persistence repository contract."""

    async def get(self, entity_id: uuid.UUID) -> T | None:
        """Return one entity by primary key."""

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int | None = None,
        include_deleted: bool = False,
    ) -> Sequence[T]:
        """Return entities with optional pagination."""

    async def add(self, entity: T) -> T:
        """Persist a new entity."""

    async def remove(self, entity: T) -> None:
        """Remove an entity from the current session."""

    async def exists(self, entity_id: uuid.UUID, *, include_deleted: bool = False) -> bool:
        """Return whether an entity exists by primary key."""
