"""RC1.6 local FileSystemStorage tests."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from rag_enterprise.knowledge.infrastructure.filesystem import FileSystemStorage
from rag_enterprise.knowledge.infrastructure.storage import (
    staging_storage_key,
    storage_key_for_version,
)

ORG_ID = uuid.UUID("018f0000-0000-7000-8000-00000000f001")
WORKSPACE_ID = uuid.UUID("018f0000-0000-7000-8000-00000000f002")
KB_ID = uuid.UUID("018f0000-0000-7000-8000-00000000f003")
DOC_ID = uuid.UUID("018f0000-0000-7000-8000-00000000f004")
VERSION_ID = uuid.UUID("018f0000-0000-7000-8000-00000000f005")


@pytest.mark.asyncio
async def test_put_get_delete_round_trip(tmp_path: Path) -> None:
    storage = FileSystemStorage(tmp_path)
    key = storage_key_for_version(
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
        knowledge_base_id=KB_ID,
        document_id=DOC_ID,
        version_id=VERSION_ID,
        file_name="handbook.txt",
    )

    stored = await storage.put(
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
        key=key,
        data=b"hello-file",
        content_type="text/plain",
    )
    assert stored.key == key

    on_disk = (
        tmp_path
        / str(ORG_ID)
        / str(WORKSPACE_ID)
        / str(DOC_ID)
        / str(VERSION_ID)
        / ("handbook.txt")
    )
    assert on_disk.is_file()
    assert on_disk.read_bytes() == b"hello-file"
    assert await storage.get(key=key) == b"hello-file"

    await storage.delete(key=key)
    assert not on_disk.exists()
    with pytest.raises(KeyError):
        await storage.get(key=key)


@pytest.mark.asyncio
async def test_creates_directories_automatically(tmp_path: Path) -> None:
    root = tmp_path / "storage" / "uploads"
    storage = FileSystemStorage(root)
    key = staging_storage_key(
        uuid.uuid4(),
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
    )
    await storage.put(
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
        key=key,
        data=b"staged",
    )
    assert (root / key).is_file()


@pytest.mark.asyncio
async def test_rejects_path_traversal(tmp_path: Path) -> None:
    storage = FileSystemStorage(tmp_path)
    with pytest.raises(ValueError, match="\\.\\."):
        await storage.put(
            organization_id=ORG_ID,
            workspace_id=WORKSPACE_ID,
            key="../escape.bin",
            data=b"nope",
        )


def test_storage_key_layout() -> None:
    key = storage_key_for_version(
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
        knowledge_base_id=KB_ID,
        document_id=DOC_ID,
        version_id=VERSION_ID,
        file_name="path/../policy.txt",
    )
    assert key == (f"{ORG_ID}/{WORKSPACE_ID}/{DOC_ID}/{VERSION_ID}/policy.txt")
    assert ".." not in key
