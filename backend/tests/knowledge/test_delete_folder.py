"""Permanent folder deletion tests."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from rag_enterprise.indexing.constants import DEFAULT_EMBEDDING_MODEL_ID
from rag_enterprise.indexing.enums import ChunkStatus, IndexStatus
from rag_enterprise.indexing.models import Chunk, Embedding
from rag_enterprise.knowledge.enums import DocumentStatus, KnowledgeBaseStatus
from rag_enterprise.knowledge.infrastructure.storage import InMemoryFileStorage
from rag_enterprise.knowledge.models import Document, DocumentVersion, Folder, KnowledgeBase
from rag_enterprise.main import create_app
from tests.helpers.rag_seed import content_hash


@pytest.fixture
async def knowledge_client(knowledge_container, actor_headers: dict[str, str]) -> AsyncClient:
    app = create_app()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=actor_headers,
    ) as client:
        yield client


async def _create_kb(client: AsyncClient, workspace_id: uuid.UUID, name: str) -> str:
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases",
        json={"name": name, "default_language": "en"},
    )
    assert response.status_code == 201
    return str(response.json()["data"]["id"])


async def _create_folder(
    client: AsyncClient,
    workspace_id: uuid.UUID,
    kb_id: str,
    name: str,
    *,
    parent_folder_id: str | None = None,
) -> str:
    body: dict[str, object] = {"name": name}
    if parent_folder_id is not None:
        body["parent_folder_id"] = parent_folder_id
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/folders",
        json=body,
    )
    assert response.status_code == 201
    return str(response.json()["data"]["id"])


async def _create_document(
    client: AsyncClient,
    workspace_id: uuid.UUID,
    kb_id: str,
    title: str,
    *,
    folder_id: str | None = None,
) -> str:
    body: dict[str, object] = {"title": title}
    if folder_id is not None:
        body["folder_id"] = folder_id
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/documents",
        json=body,
    )
    assert response.status_code == 201
    return str(response.json()["data"]["id"])


@pytest.mark.asyncio
async def test_delete_empty_folder(
    knowledge_client: AsyncClient,
    workspace_id: uuid.UUID,
) -> None:
    kb_id = await _create_kb(knowledge_client, workspace_id, "Empty Folder KB")
    folder_id = await _create_folder(knowledge_client, workspace_id, kb_id, "Empty")

    deleted = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/folders/{folder_id}"
    )
    assert deleted.status_code == 204

    contents = await knowledge_client.get(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/contents"
    )
    assert contents.status_code == 200
    assert contents.json()["data"]["folders"] == []


@pytest.mark.asyncio
async def test_delete_folder_with_documents(
    knowledge_client: AsyncClient,
    workspace_id: uuid.UUID,
) -> None:
    kb_id = await _create_kb(knowledge_client, workspace_id, "Docs Folder KB")
    folder_a = await _create_folder(knowledge_client, workspace_id, kb_id, "A")
    folder_b = await _create_folder(knowledge_client, workspace_id, kb_id, "B")
    doc_a = await _create_document(
        knowledge_client, workspace_id, kb_id, "In A", folder_id=folder_a
    )
    doc_b = await _create_document(
        knowledge_client, workspace_id, kb_id, "In B", folder_id=folder_b
    )

    deleted = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/folders/{folder_a}"
    )
    assert deleted.status_code == 204

    missing_doc = await knowledge_client.get(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/documents/{doc_a}"
    )
    assert missing_doc.status_code == 404

    kept_doc = await knowledge_client.get(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/documents/{doc_b}"
    )
    assert kept_doc.status_code == 200

    contents = await knowledge_client.get(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/contents"
    )
    names = {item["name"] for item in contents.json()["data"]["folders"]}
    assert names == {"B"}


@pytest.mark.asyncio
async def test_delete_folder_twice_returns_404(
    knowledge_client: AsyncClient,
    workspace_id: uuid.UUID,
) -> None:
    kb_id = await _create_kb(knowledge_client, workspace_id, "Twice Folder KB")
    folder_id = await _create_folder(knowledge_client, workspace_id, kb_id, "Twice")

    first = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/folders/{folder_id}"
    )
    assert first.status_code == 204
    second = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/folders/{folder_id}"
    )
    assert second.status_code == 404
    assert second.json()["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_delete_folder_wrong_kb_returns_404(
    knowledge_client: AsyncClient,
    workspace_id: uuid.UUID,
) -> None:
    kb_a = await _create_kb(knowledge_client, workspace_id, "KB A")
    kb_b = await _create_kb(knowledge_client, workspace_id, "KB B")
    folder_id = await _create_folder(knowledge_client, workspace_id, kb_a, "Owned by A")

    response = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_b}/folders/{folder_id}"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_indexed_folder_removes_cascade_and_keeps_sibling(
    knowledge_client: AsyncClient,
    knowledge_container,
    knowledge_session_factory,
    workspace_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    storage = knowledge_container.file_storage
    assert isinstance(storage, InMemoryFileStorage)

    kb_id = uuid.UUID(await _create_kb(knowledge_client, workspace_id, "Indexed Folder KB"))
    await knowledge_client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/publish"
    )
    folder_a = uuid.UUID(
        await _create_folder(knowledge_client, workspace_id, str(kb_id), "Folder A")
    )
    folder_b = uuid.UUID(
        await _create_folder(knowledge_client, workspace_id, str(kb_id), "Folder B")
    )
    doc_a = uuid.UUID(
        await _create_document(
            knowledge_client, workspace_id, str(kb_id), "Doc A", folder_id=str(folder_a)
        )
    )
    doc_b = uuid.UUID(
        await _create_document(
            knowledge_client, workspace_id, str(kb_id), "Doc B", folder_id=str(folder_b)
        )
    )

    original_key = f"{org_id}/{workspace_id}/{doc_a}/ver/doc.txt"
    extracted_key = f"{org_id}/{workspace_id}/{doc_a}/ver/doc.extracted.txt"
    await storage.put(
        organization_id=org_id,
        workspace_id=workspace_id,
        key=original_key,
        data=b"alpha content",
        content_type="text/plain",
    )
    await storage.put(
        organization_id=org_id,
        workspace_id=workspace_id,
        key=extracted_key,
        data=b"alpha content",
        content_type="text/plain",
    )

    async with knowledge_session_factory() as session:
        for document_id, text, key in (
            (doc_a, "alpha content", original_key),
            (doc_b, "beta content", "keep/original"),
        ):
            version = DocumentVersion(
                organization_id=org_id,
                workspace_id=workspace_id,
                knowledge_base_id=kb_id,
                document_id=document_id,
                version_number=1,
                content_hash=content_hash(text),
                file_name="doc.txt",
                file_size_bytes=len(text),
                mime_type="text/plain",
                storage_key_original=key if document_id == doc_a else "keep/original",
                storage_key_extracted=extracted_key if document_id == doc_a else None,
            )
            session.add(version)
            await session.flush()
            document = await session.get(Document, document_id)
            assert document is not None
            document.current_version_id = version.id
            document.status = DocumentStatus.ACTIVE
            chunk = Chunk(
                organization_id=org_id,
                workspace_id=workspace_id,
                knowledge_base_id=kb_id,
                document_id=document_id,
                document_version_id=version.id,
                sequence_number=0,
                text=text,
                content_hash=content_hash(text),
                start_offset=0,
                end_offset=len(text),
                status=ChunkStatus.INDEXED,
            )
            session.add(chunk)
            await session.flush()
            if document_id == doc_a:
                session.add(
                    Embedding(
                        organization_id=org_id,
                        workspace_id=workspace_id,
                        chunk_id=chunk.id,
                        document_version_id=version.id,
                        knowledge_base_id=kb_id,
                        embedding_model_id=DEFAULT_EMBEDDING_MODEL_ID,
                        model_key="test-model",
                        vector=[0.1] * 1024,
                        dimensions=1024,
                        content_hash=content_hash(text),
                        generation=1,
                        index_status=IndexStatus.INDEXED,
                    )
                )

        kb = await session.get(KnowledgeBase, kb_id)
        assert kb is not None
        kb.status = KnowledgeBaseStatus.ACTIVE
        kb.document_count = 2
        await session.commit()

    deleted = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/folders/{folder_a}"
    )
    assert deleted.status_code == 204

    async with knowledge_session_factory() as session:
        assert (await session.get(Folder, folder_a)) is None
        assert (await session.get(Folder, folder_b)) is not None
        assert (await session.get(Document, doc_a)) is None
        assert (await session.get(Document, doc_b)) is not None
        assert (
            await session.scalar(
                select(func.count()).select_from(Chunk).where(Chunk.document_id == doc_a)
            )
        ) == 0
        assert (
            await session.scalar(
                select(func.count()).select_from(Chunk).where(Chunk.document_id == doc_b)
            )
        ) == 1
        kb = await session.get(KnowledgeBase, kb_id)
        assert kb is not None
        assert kb.document_count == 1

    with pytest.raises(KeyError):
        await storage.get(key=original_key)
    with pytest.raises(KeyError):
        await storage.get(key=extracted_key)


@pytest.mark.asyncio
async def test_delete_folder_recursive_nested(
    knowledge_client: AsyncClient,
    workspace_id: uuid.UUID,
) -> None:
    kb_id = await _create_kb(knowledge_client, workspace_id, "Nested Folder KB")
    parent = await _create_folder(knowledge_client, workspace_id, kb_id, "Parent")
    child = await _create_folder(
        knowledge_client, workspace_id, kb_id, "Child", parent_folder_id=parent
    )
    await _create_document(knowledge_client, workspace_id, kb_id, "Nested Doc", folder_id=child)
    sibling = await _create_folder(knowledge_client, workspace_id, kb_id, "Sibling")

    deleted = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/folders/{parent}"
    )
    assert deleted.status_code == 204

    tree = await knowledge_client.get(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/tree"
    )
    assert tree.status_code == 200
    roots = tree.json()["data"]["folders"]
    assert len(roots) == 1
    assert roots[0]["id"] == sibling
    assert roots[0]["children"] == []

    child_contents = await knowledge_client.get(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/contents",
        params={"folder_id": child},
    )
    assert child_contents.status_code == 404


@pytest.mark.asyncio
async def test_delete_folder_legal_hold_rolls_back(
    knowledge_client: AsyncClient,
    knowledge_session_factory,
    workspace_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    kb_id = uuid.UUID(await _create_kb(knowledge_client, workspace_id, "Hold Folder KB"))
    folder_id = uuid.UUID(
        await _create_folder(knowledge_client, workspace_id, str(kb_id), "Protected")
    )
    doc_id = uuid.UUID(
        await _create_document(
            knowledge_client, workspace_id, str(kb_id), "Held", folder_id=str(folder_id)
        )
    )
    async with knowledge_session_factory() as session:
        document = await session.get(Document, doc_id)
        assert document is not None
        document.legal_hold = True
        session.add(
            DocumentVersion(
                organization_id=org_id,
                workspace_id=workspace_id,
                knowledge_base_id=kb_id,
                document_id=doc_id,
                version_number=1,
                content_hash=content_hash("hold"),
                file_name="hold.txt",
                file_size_bytes=4,
                mime_type="text/plain",
                storage_key_original="hold/original",
            )
        )
        await session.commit()

    response = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/folders/{folder_id}"
    )
    assert response.status_code == 409

    async with knowledge_session_factory() as session:
        assert (await session.get(Folder, folder_id)) is not None
        assert (await session.get(Document, doc_id)) is not None


@pytest.mark.asyncio
async def test_delete_folder_tolerates_missing_storage_files(
    knowledge_client: AsyncClient,
    knowledge_session_factory,
    workspace_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    kb_id = uuid.UUID(await _create_kb(knowledge_client, workspace_id, "Ghost Folder KB"))
    folder_id = uuid.UUID(await _create_folder(knowledge_client, workspace_id, str(kb_id), "Ghost"))
    doc_id = uuid.UUID(
        await _create_document(
            knowledge_client, workspace_id, str(kb_id), "Ghost Doc", folder_id=str(folder_id)
        )
    )
    async with knowledge_session_factory() as session:
        session.add(
            DocumentVersion(
                organization_id=org_id,
                workspace_id=workspace_id,
                knowledge_base_id=kb_id,
                document_id=doc_id,
                version_number=1,
                content_hash=content_hash("x"),
                file_name="ghost.txt",
                file_size_bytes=1,
                mime_type="text/plain",
                storage_key_original="missing/original",
                storage_key_extracted="missing/extracted",
            )
        )
        await session.commit()

    deleted = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/folders/{folder_id}"
    )
    assert deleted.status_code == 204
