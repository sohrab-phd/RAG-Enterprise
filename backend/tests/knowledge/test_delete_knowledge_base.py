"""Knowledge base permanent deletion tests."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from rag_enterprise.generation.persistence import Conversation, Message
from rag_enterprise.indexing.constants import DEFAULT_EMBEDDING_MODEL_ID
from rag_enterprise.indexing.enums import ChunkStatus, IndexStatus
from rag_enterprise.indexing.models import Chunk, Embedding
from rag_enterprise.knowledge.enums import DocumentStatus, FolderStatus, KnowledgeBaseStatus
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


@pytest.mark.asyncio
async def test_delete_empty_knowledge_base(
    knowledge_client: AsyncClient,
    workspace_id: uuid.UUID,
) -> None:
    kb_id = await _create_kb(knowledge_client, workspace_id, "Empty KB")
    deleted = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}"
    )
    assert deleted.status_code == 204

    missing = await knowledge_client.get(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}"
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_delete_knowledge_base_twice_returns_404(
    knowledge_client: AsyncClient,
    workspace_id: uuid.UUID,
) -> None:
    kb_id = await _create_kb(knowledge_client, workspace_id, "Twice KB")
    first = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}"
    )
    assert first.status_code == 204
    second = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}"
    )
    assert second.status_code == 404
    assert second.json()["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_delete_unknown_knowledge_base_returns_404(
    knowledge_client: AsyncClient,
    workspace_id: uuid.UUID,
) -> None:
    response = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{uuid.uuid4()}"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_kb_with_documents_versions_chunks_embeddings_and_files(
    knowledge_client: AsyncClient,
    knowledge_container,
    knowledge_session_factory,
    workspace_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    storage = knowledge_container.file_storage
    assert isinstance(storage, InMemoryFileStorage)

    kb_id = uuid.UUID(await _create_kb(knowledge_client, workspace_id, "Full KB"))
    await knowledge_client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/publish"
    )

    original_key = f"{org_id}/{workspace_id}/doc/ver/handbook.txt"
    extracted_key = f"{org_id}/{workspace_id}/doc/ver/handbook.extracted.txt"
    await storage.put(
        organization_id=org_id,
        workspace_id=workspace_id,
        key=original_key,
        data=b"hello",
        content_type="text/plain",
    )
    await storage.put(
        organization_id=org_id,
        workspace_id=workspace_id,
        key=extracted_key,
        data=b"hello extracted",
        content_type="text/plain",
    )

    async with knowledge_session_factory() as session:
        folder = Folder(
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            name="Root",
            path="/Root",
            depth=0,
            status=FolderStatus.ACTIVE,
        )
        session.add(folder)
        await session.flush()

        document = Document(
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            folder_id=folder.id,
            title="Handbook",
            status=DocumentStatus.ACTIVE,
            declared_language="en",
        )
        session.add(document)
        await session.flush()

        version = DocumentVersion(
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            document_id=document.id,
            version_number=1,
            content_hash=content_hash("hello"),
            file_name="handbook.txt",
            file_size_bytes=5,
            mime_type="text/plain",
            storage_key_original=original_key,
            storage_key_extracted=extracted_key,
        )
        session.add(version)
        await session.flush()
        document.current_version_id = version.id

        chunk = Chunk(
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            document_id=document.id,
            document_version_id=version.id,
            sequence_number=0,
            text="hello",
            content_hash=content_hash("hello"),
            start_offset=0,
            end_offset=5,
            status=ChunkStatus.INDEXED,
        )
        session.add(chunk)
        await session.flush()

        embedding = Embedding(
            organization_id=org_id,
            workspace_id=workspace_id,
            chunk_id=chunk.id,
            document_version_id=version.id,
            knowledge_base_id=kb_id,
            embedding_model_id=DEFAULT_EMBEDDING_MODEL_ID,
            model_key="test-model",
            vector=[0.1] * 1024,
            dimensions=1024,
            content_hash=content_hash("hello"),
            generation=1,
            index_status=IndexStatus.INDEXED,
        )
        session.add(embedding)

        conversation = Conversation(
            organization_id=org_id,
            workspace_id=workspace_id,
            user_id=user_id,
            knowledge_base_id=kb_id,
            status="active",
        )
        session.add(conversation)
        await session.flush()
        session.add(
            Message(
                organization_id=org_id,
                workspace_id=workspace_id,
                conversation_id=conversation.id,
                knowledge_base_id=kb_id,
                role="user",
                content="hi",
                sequence_number=1,
            )
        )
        await session.commit()

    deleted = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}"
    )
    assert deleted.status_code == 204

    async with knowledge_session_factory() as session:

        async def count_for(model: type[object], column: object) -> int:
            value = await session.scalar(
                select(func.count()).select_from(model).where(column == kb_id)  # type: ignore[arg-type]
            )
            return int(value or 0)

        assert await count_for(KnowledgeBase, KnowledgeBase.id) == 0
        assert await count_for(Document, Document.knowledge_base_id) == 0
        assert await count_for(DocumentVersion, DocumentVersion.knowledge_base_id) == 0
        assert await count_for(Folder, Folder.knowledge_base_id) == 0
        assert await count_for(Chunk, Chunk.knowledge_base_id) == 0
        assert await count_for(Embedding, Embedding.knowledge_base_id) == 0
        assert await count_for(Conversation, Conversation.knowledge_base_id) == 0
        assert await count_for(Message, Message.knowledge_base_id) == 0

    with pytest.raises(KeyError):
        await storage.get(key=original_key)
    with pytest.raises(KeyError):
        await storage.get(key=extracted_key)


@pytest.mark.asyncio
async def test_delete_kb_legal_hold_rolls_back(
    knowledge_client: AsyncClient,
    knowledge_session_factory,
    workspace_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    kb_id = uuid.UUID(await _create_kb(knowledge_client, workspace_id, "Hold KB"))
    async with knowledge_session_factory() as session:
        document = Document(
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            title="Protected",
            status=DocumentStatus.ACTIVE,
            declared_language="en",
            legal_hold=True,
        )
        session.add(document)
        await session.commit()

    response = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}"
    )
    assert response.status_code == 409

    async with knowledge_session_factory() as session:
        kb = await session.get(KnowledgeBase, kb_id)
        assert kb is not None
        assert kb.status == KnowledgeBaseStatus.DRAFT
        docs = (
            await session.scalars(select(Document).where(Document.knowledge_base_id == kb_id))
        ).all()
        assert len(docs) == 1


@pytest.mark.asyncio
async def test_list_excludes_deleted_knowledge_base(
    knowledge_client: AsyncClient,
    workspace_id: uuid.UUID,
) -> None:
    kb_id = await _create_kb(knowledge_client, workspace_id, "Listed Then Gone")
    deleted = await knowledge_client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}"
    )
    assert deleted.status_code == 204
    listed = await knowledge_client.get(f"/api/v1/workspaces/{workspace_id}/knowledge-bases")
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()["data"]["items"]}
    assert kb_id not in ids


@pytest.mark.asyncio
async def test_delete_tolerates_missing_storage_files(
    knowledge_client: AsyncClient,
    knowledge_session_factory,
    workspace_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    kb_id = uuid.UUID(await _create_kb(knowledge_client, workspace_id, "Missing Files KB"))
    async with knowledge_session_factory() as session:
        document = Document(
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            title="Ghost",
            status=DocumentStatus.ACTIVE,
            declared_language="en",
        )
        session.add(document)
        await session.flush()
        session.add(
            DocumentVersion(
                organization_id=org_id,
                workspace_id=workspace_id,
                knowledge_base_id=kb_id,
                document_id=document.id,
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
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}"
    )
    assert deleted.status_code == 204
