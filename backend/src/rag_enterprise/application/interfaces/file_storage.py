"""File storage interface."""

from __future__ import annotations

import uuid
from typing import Protocol


class StoredObject(Protocol):
    """Reference to an object stored outside the database."""

    @property
    def key(self) -> str:
        """Return the storage object key."""

    @property
    def content_type(self) -> str | None:
        """Return the stored content type when known."""


class FileStorage(Protocol):
    """Store and retrieve binary payloads such as uploads and extracted text."""

    async def put(
        self,
        *,
        organization_id: uuid.UUID,
        workspace_id: uuid.UUID,
        key: str,
        data: bytes,
        content_type: str | None = None,
    ) -> StoredObject:
        """Store a binary object and return its reference."""

    async def get(self, *, key: str) -> bytes:
        """Retrieve a stored object by key."""

    async def delete(self, *, key: str) -> None:
        """Delete a stored object by key."""
