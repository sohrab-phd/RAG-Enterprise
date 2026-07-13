"""Knowledge repository tests."""

import uuid

import pytest

from rag_enterprise.knowledge.enums import KnowledgeBaseStatus
from rag_enterprise.knowledge.models import KnowledgeBase
from rag_enterprise.knowledge.repositories import KnowledgeBaseRepository, TenantScope


@pytest.mark.asyncio
async def test_knowledge_base_repository_scopes_by_workspace(
    knowledge_session_factory,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    other_workspace = uuid.UUID("018f0000-0000-7000-8000-000000000099")
    scope = TenantScope(org_id, workspace_id)
    async with knowledge_session_factory() as session:
        repo = KnowledgeBaseRepository(session)
        kb = KnowledgeBase(
            organization_id=org_id,
            workspace_id=workspace_id,
            name="Policies",
            status=KnowledgeBaseStatus.DRAFT,
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )
        other = KnowledgeBase(
            organization_id=org_id,
            workspace_id=other_workspace,
            name="Other",
            status=KnowledgeBaseStatus.DRAFT,
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )
        await repo.add(kb)
        await repo.add(other)
        await session.commit()

    async with knowledge_session_factory() as session:
        repo = KnowledgeBaseRepository(session)
        items = await repo.list_scoped(scope)
        assert len(items) == 1
        assert items[0].name == "Policies"


@pytest.mark.asyncio
async def test_soft_deleted_knowledge_base_is_hidden(
    knowledge_session_factory,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    from datetime import UTC, datetime

    scope = TenantScope(org_id, workspace_id)
    async with knowledge_session_factory() as session:
        repo = KnowledgeBaseRepository(session)
        kb = KnowledgeBase(
            organization_id=org_id,
            workspace_id=workspace_id,
            name="ToDelete",
            status=KnowledgeBaseStatus.DELETED,
            deleted_at=datetime.now(UTC),
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )
        await repo.add(kb)
        await session.commit()
        kb_id = kb.id

    async with knowledge_session_factory() as session:
        repo = KnowledgeBaseRepository(session)
        assert await repo.get_scoped(scope, kb_id) is None
