"""In-memory file storage for development and tests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(slots=True)
class _StoredObject:
    key: str
    content_type: str | None
    data: bytes


class InMemoryFileStorage:
    """Simple dict-backed file storage."""

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
    return (
        f"org/{organization_id}/workspace/{workspace_id}/"
        f"knowledge-base/{knowledge_base_id}/document/{document_id}/"
        f"version/{version_id}/original/{file_name}"
    )


def staging_storage_key(upload_id: uuid.UUID) -> str:
    return f"uploads/staging/{upload_id}"
