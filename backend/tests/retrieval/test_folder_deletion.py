"""Retrieval must not return chunks from permanently deleted folders."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.indexing.service import IndexingService
from rag_enterprise.knowledge.commands import DeleteFolderCommand
from rag_enterprise.knowledge.context import RequestActor
from rag_enterprise.knowledge.enums import FolderStatus
from rag_enterprise.knowledge.handlers.command_handlers import DeleteFolderHandler
from rag_enterprise.knowledge.infrastructure.storage import InMemoryFileStorage
from rag_enterprise.knowledge.models import Folder
from rag_enterprise.retrieval.models import SearchRequest
from rag_enterprise.retrieval.service import RetrievalService
from tests.helpers.rag_seed import ALL_PERMISSIONS, seed_chunked_version


@pytest.mark.asyncio
async def test_retrieval_after_folder_deletion_excludes_folder_docs(
    rag_session_factory: async_sessionmaker[AsyncSession],
    indexing_service: IndexingService,
    retrieval_service: RetrievalService,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    storage = InMemoryFileStorage()
    async with rag_session_factory() as session:
        kb, document, version, _ = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=["unique folder phrase about benefits policy", "still benefits"],
        )
        folder = Folder(
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb.id,
            parent_folder_id=None,
            name="Policies",
            path="/Policies",
            depth=0,
            status=FolderStatus.ACTIVE,
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )
        session.add(folder)
        await session.flush()
        document.folder_id = folder.id
        await session.commit()
        kb_id = kb.id
        folder_id = folder.id
        document_id = document.id
        version_id = version.id

    await indexing_service.index_document_version(version_id)

    before = await retrieval_service.retrieve(
        SearchRequest(
            query_text="unique folder phrase about benefits policy",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            top_k=5,
            permissions=ALL_PERMISSIONS,
        )
    )
    assert before.result_count >= 1
    assert any(item.document_id == document_id for item in before.results)

    handler = DeleteFolderHandler(rag_session_factory, storage)
    result = await handler.handle(
        DeleteFolderCommand(
            actor=RequestActor(
                user_id=user_id,
                organization_id=org_id,
                permissions=ALL_PERMISSIONS,
            ),
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            folder_id=folder_id,
        )
    )
    assert result.is_success

    after = await retrieval_service.retrieve(
        SearchRequest(
            query_text="unique folder phrase about benefits policy",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            top_k=5,
            permissions=ALL_PERMISSIONS,
        )
    )
    assert all(item.document_id != document_id for item in after.results)
