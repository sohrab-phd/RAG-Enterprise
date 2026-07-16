"""Permanent document deletion tests."""

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
from rag_enterprise.knowledge.models import Document, DocumentVersion, KnowledgeBase
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


async def _create_document(
    client: AsyncClient,
    workspace_id: uuid.UUID,
    kb_id: str,
    title: str,
) -> str:
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/documents",
        json={"title": title},
    )
    assert response.status_code == 201
    return str(response.json()["data"]["id"])


@pytest.mark.asyncio
async def test_delete_existing_document(
    knowledge_client: AsyncClient,
    workspace_id: uuid.UUID,
) -> None:
    kb_id = await _create_kb(knowledge_client, workspace_id, "Doc Delete KB")
    doc_id = await _create_document(knowledge_client, workspace_id, kb_id, "Handbook")

    deleted = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/documents/{doc_id}"
    )
    assert deleted.status_code == 204

    missing = await knowledge_client.get(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/documents/{doc_id}"
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_twice_returns_404(
    knowledge_client: AsyncClient,
    workspace_id: uuid.UUID,
) -> None:
    kb_id = await _create_kb(knowledge_client, workspace_id, "Twice Doc KB")
    doc_id = await _create_document(knowledge_client, workspace_id, kb_id, "Twice")

    first = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/documents/{doc_id}"
    )
    assert first.status_code == 204
    second = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/documents/{doc_id}"
    )
    assert second.status_code == 404
    assert second.json()["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_delete_document_wrong_kb_returns_404(
    knowledge_client: AsyncClient,
    workspace_id: uuid.UUID,
) -> None:
    kb_a = await _create_kb(knowledge_client, workspace_id, "KB A")
    kb_b = await _create_kb(knowledge_client, workspace_id, "KB B")
    doc_id = await _create_document(knowledge_client, workspace_id, kb_a, "Owned by A")

    response = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_b}/documents/{doc_id}"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_indexed_document_removes_versions_chunks_embeddings_files(
    knowledge_client: AsyncClient,
    knowledge_container,
    knowledge_session_factory,
    workspace_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    storage = knowledge_container.file_storage
    assert isinstance(storage, InMemoryFileStorage)

    kb_id = uuid.UUID(await _create_kb(knowledge_client, workspace_id, "Indexed Doc KB"))
    await knowledge_client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/publish"
    )
    doc_id = uuid.UUID(
        await _create_document(knowledge_client, workspace_id, str(kb_id), "Indexed Doc")
    )

    original_key = f"{org_id}/{workspace_id}/{doc_id}/ver/doc.txt"
    extracted_key = f"{org_id}/{workspace_id}/{doc_id}/ver/doc.extracted.txt"
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

    other_doc_id: uuid.UUID
    async with knowledge_session_factory() as session:
        version = DocumentVersion(
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            document_id=doc_id,
            version_number=1,
            content_hash=content_hash("alpha content"),
            file_name="doc.txt",
            file_size_bytes=13,
            mime_type="text/plain",
            storage_key_original=original_key,
            storage_key_extracted=extracted_key,
        )
        session.add(version)
        await session.flush()

        document = await session.get(Document, doc_id)
        assert document is not None
        document.current_version_id = version.id
        document.status = DocumentStatus.ACTIVE

        chunk = Chunk(
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            document_id=doc_id,
            document_version_id=version.id,
            sequence_number=0,
            text="alpha content",
            content_hash=content_hash("alpha content"),
            start_offset=0,
            end_offset=13,
            status=ChunkStatus.INDEXED,
        )
        session.add(chunk)
        await session.flush()
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
                content_hash=content_hash("alpha content"),
                generation=1,
                index_status=IndexStatus.INDEXED,
            )
        )

        other = Document(
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            title="Keep Me",
            status=DocumentStatus.ACTIVE,
            declared_language="en",
        )
        session.add(other)
        await session.flush()
        other_doc_id = other.id
        other_version = DocumentVersion(
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            document_id=other.id,
            version_number=1,
            content_hash=content_hash("beta"),
            file_name="keep.txt",
            file_size_bytes=4,
            mime_type="text/plain",
            storage_key_original="keep/original",
            storage_key_extracted=None,
        )
        session.add(other_version)
        await session.flush()
        other.current_version_id = other_version.id
        session.add(
            Chunk(
                organization_id=org_id,
                workspace_id=workspace_id,
                knowledge_base_id=kb_id,
                document_id=other.id,
                document_version_id=other_version.id,
                sequence_number=0,
                text="beta",
                content_hash=content_hash("beta"),
                start_offset=0,
                end_offset=4,
                status=ChunkStatus.INDEXED,
            )
        )

        kb = await session.get(KnowledgeBase, kb_id)
        assert kb is not None
        kb.status = KnowledgeBaseStatus.ACTIVE
        kb.document_count = 2
        await session.commit()

    deleted = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/documents/{doc_id}"
    )
    assert deleted.status_code == 204

    async with knowledge_session_factory() as session:
        assert (
            await session.scalar(
                select(func.count()).select_from(Document).where(Document.id == doc_id)
            )
        ) == 0
        assert (
            await session.scalar(
                select(func.count())
                .select_from(DocumentVersion)
                .where(DocumentVersion.document_id == doc_id)
            )
        ) == 0
        assert (
            await session.scalar(
                select(func.count()).select_from(Chunk).where(Chunk.document_id == doc_id)
            )
        ) == 0
        remaining_chunks = (
            await session.scalars(select(Chunk).where(Chunk.document_id == other_doc_id))
        ).all()
        assert len(remaining_chunks) == 1
        kept = await session.get(Document, other_doc_id)
        assert kept is not None
        kb = await session.get(KnowledgeBase, kb_id)
        assert kb is not None
        assert kb.document_count == 1

    with pytest.raises(KeyError):
        await storage.get(key=original_key)
    with pytest.raises(KeyError):
        await storage.get(key=extracted_key)


@pytest.mark.asyncio
async def test_delete_document_legal_hold_rolls_back(
    knowledge_client: AsyncClient,
    knowledge_session_factory,
    workspace_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    kb_id = uuid.UUID(await _create_kb(knowledge_client, workspace_id, "Hold Doc KB"))
    doc_id = uuid.UUID(
        await _create_document(knowledge_client, workspace_id, str(kb_id), "Protected")
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
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/documents/{doc_id}"
    )
    assert response.status_code == 409

    async with knowledge_session_factory() as session:
        document = await session.get(Document, doc_id)
        assert document is not None
        versions = (
            await session.scalars(
                select(DocumentVersion).where(DocumentVersion.document_id == doc_id)
            )
        ).all()
        assert len(versions) == 1


@pytest.mark.asyncio
async def test_delete_tolerates_missing_storage_files(
    knowledge_client: AsyncClient,
    knowledge_session_factory,
    workspace_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    kb_id = uuid.UUID(await _create_kb(knowledge_client, workspace_id, "Ghost Files KB"))
    doc_id = uuid.UUID(await _create_document(knowledge_client, workspace_id, str(kb_id), "Ghost"))
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
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/documents/{doc_id}"
    )
    assert deleted.status_code == 204
