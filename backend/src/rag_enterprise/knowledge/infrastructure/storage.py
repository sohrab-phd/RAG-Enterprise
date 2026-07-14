"""In-memory file storage for unit tests, plus opaque storage key helpers."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class _StoredObject:
    key: str
    content_type: str | None
    data: bytes


class InMemoryFileStorage:
    """Dict-backed file storage for isolated unit/component tests."""

    def __init__(self) -> None:
        self._objects: dict[str, _StoredObject] = {}

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
        obj = _StoredObject(key=key, content_type=content_type, data=data)
        self._objects[key] = obj
        return obj

    async def get(self, *, key: str) -> bytes:
        return self._objects[key].data

    async def delete(self, *, key: str) -> None:
        self._objects.pop(key, None)


def storage_key_for_version(
    *,
    organization_id: uuid.UUID,
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    file_name: str,
) -> str:
    """Return a relative object key under ``FILE_STORAGE_ROOT``.

    Layout::

        {organization_id}/{workspace_id}/{document_id}/{document_version_id}/{file_name}
    """
    del knowledge_base_id
    safe_name = Path(file_name).name or "upload.bin"
    return f"{organization_id}/{workspace_id}/{document_id}/{version_id}/{safe_name}"


def staging_storage_key(
    upload_id: uuid.UUID,
    *,
    organization_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> str:
    """Return a staging key under org/workspace before version binding."""
    return f"{organization_id}/{workspace_id}/staging/{upload_id}"
