"""Conversation repositories."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import cast

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_enterprise.db.repositories.base import SQLAlchemyRepository
from rag_enterprise.db.result_utils import result_rowcount
from rag_enterprise.generation.models import ConversationStatus, MessageRole, MessageTurn
from rag_enterprise.generation.persistence import Conversation, Message
from rag_enterprise.knowledge.repositories.scope import TenantScope


class ConversationRepository(SQLAlchemyRepository[Conversation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Conversation)

    async def get_scoped(
        self,
        scope: TenantScope,
        conversation_id: uuid.UUID,
    ) -> Conversation | None:
        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == scope.organization_id,
            Conversation.workspace_id == scope.workspace_id,
            Conversation.status == ConversationStatus.ACTIVE,
        )
        return cast(Conversation | None, await self._session.scalar(statement))

    async def delete_all_for_knowledge_base(self, knowledge_base_id: uuid.UUID) -> int:
        result = await self._session.execute(
            delete(Conversation).where(Conversation.knowledge_base_id == knowledge_base_id)
        )
        return result_rowcount(result)


class MessageRepository(SQLAlchemyRepository[Message]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Message)

    async def list_recent_turns(
        self,
        conversation_id: uuid.UUID,
        *,
        limit: int,
    ) -> list[MessageTurn]:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .where(Message.role.in_([MessageRole.USER, MessageRole.ASSISTANT]))
            .order_by(Message.sequence_number.desc())
            .limit(limit)
        )
        rows = list((await self._session.scalars(statement)).all())
        rows.reverse()
        return [MessageTurn(role=MessageRole(row.role), content=row.content) for row in rows]

    async def next_sequence(self, conversation_id: uuid.UUID) -> int:
        statement = select(func.coalesce(func.max(Message.sequence_number), 0)).where(
            Message.conversation_id == conversation_id
        )
        current = await self._session.scalar(statement)
        return int(current or 0) + 1

    async def list_for_conversation(
        self,
        conversation_id: uuid.UUID,
    ) -> Sequence[Message]:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_number.asc())
        )
        return (await self._session.scalars(statement)).all()

    async def delete_all_for_knowledge_base(self, knowledge_base_id: uuid.UUID) -> int:
        result = await self._session.execute(
            delete(Message).where(Message.knowledge_base_id == knowledge_base_id)
        )
        return result_rowcount(result)
