"""Knowledge command handler unit tests."""

import uuid

import pytest

from rag_enterprise.knowledge.authorization import ALL_KNOWLEDGE_PERMISSIONS
from rag_enterprise.knowledge.commands import CreateKnowledgeBaseCommand
from rag_enterprise.knowledge.context import RequestActor
from rag_enterprise.knowledge.handlers.command_handlers import CreateKnowledgeBaseHandler


@pytest.mark.asyncio
async def test_create_knowledge_base_handler(
    knowledge_session_factory,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    actor = RequestActor(
        user_id=user_id,
        organization_id=org_id,
        permissions=ALL_KNOWLEDGE_PERMISSIONS,
    )
    handler = CreateKnowledgeBaseHandler(knowledge_session_factory)
    result = await handler.handle(
        CreateKnowledgeBaseCommand(
            actor=actor,
            workspace_id=workspace_id,
            name="Runbook",
        )
    )
    assert result.is_success
    assert result.unwrap().name == "Runbook"
