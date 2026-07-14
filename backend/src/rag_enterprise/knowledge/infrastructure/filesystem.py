"""Local filesystem file storage (RC1.6)."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class _StoredObject:
    key: str
    content_type: str | None


class FileSystemStorage:
    """Persist upload binaries under a configurable local root.

    Layout (relative to ``FILE_STORAGE_ROOT``)::

        {organization_id}/{workspace_id}/{document_id}/{document_version_id}/...
        {organization_id}/{workspace_id}/staging/{upload_id}
    """

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    async def put(
        self,
        *,
        organization_id: uuid.UUID,
        workspace_id: uuid.UUID,
        key: str,
        data: bytes,
        content_type: str | None = None,
    ) -> _StoredObject:
        del organization_id, workspace_id
        path = self._resolve_key(key)
        await asyncio.to_thread(self._write_bytes, path, data)
        return _StoredObject(key=key, content_type=content_type)

    async def get(self, *, key: str) -> bytes:
        path = self._resolve_key(key)
        try:
            return await asyncio.to_thread(path.read_bytes)
        except FileNotFoundError as exc:
            raise KeyError(key) from exc

    async def delete(self, *, key: str) -> None:
        path = self._resolve_key(key)
        await asyncio.to_thread(self._unlink_if_exists, path)

    def _resolve_key(self, key: str) -> Path:
        if not key or not key.strip():
            raise ValueError("storage key must be non-empty")
        relative = Path(key)
        if relative.is_absolute():
            raise ValueError("storage key must be a relative path")
        if ".." in relative.parts:
            raise ValueError("storage key must not contain '..'")
        resolved = (self._root / relative).resolve()
        try:
            resolved.relative_to(self._root)
        except ValueError as exc:
            raise ValueError("storage key escapes storage root") from exc
        return resolved

    @staticmethod
    def _write_bytes(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    @staticmethod
    def _unlink_if_exists(path: Path) -> None:
        path.unlink(missing_ok=True)
