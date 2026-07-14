"""Knowledge base repository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import cast

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_enterprise.db.repositories.base import SQLAlchemyRepository
from rag_enterprise.knowledge.enums import KnowledgeBaseStatus
from rag_enterprise.knowledge.models import KnowledgeBase
from rag_enterprise.knowledge.repositories.scope import TenantScope


class KnowledgeBaseRepository(SQLAlchemyRepository[KnowledgeBase]):
    """Persistence access for knowledge bases."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, KnowledgeBase)

    async def get_scoped(
        self,
        scope: TenantScope,
        knowledge_base_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> KnowledgeBase | None:
        statement = self._scoped_select(scope, include_deleted=include_deleted).where(
            KnowledgeBase.id == knowledge_base_id
        )
        return cast(KnowledgeBase | None, await self._session.scalar(statement))

    async def list_scoped(
        self,
        scope: TenantScope,
        *,
        status: str | None = None,
        query: str | None = None,
        offset: int = 0,
        limit: int | None = None,
        include_deleted: bool = False,
    ) -> Sequence[KnowledgeBase]:
        statement = self._scoped_select(scope, include_deleted=include_deleted)
        if status is not None:
            statement = statement.where(KnowledgeBase.status == status)
        if query:
            statement = statement.where(KnowledgeBase.name.ilike(f"%{query}%"))
        statement = statement.order_by(KnowledgeBase.updated_at.desc()).offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.scalars(statement)
        return result.all()

    async def count_scoped(
        self,
        scope: TenantScope,
        *,
        status: str | None = None,
        query: str | None = None,
        include_deleted: bool = False,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(KnowledgeBase)
            .where(
                KnowledgeBase.organization_id == scope.organization_id,
                KnowledgeBase.workspace_id == scope.workspace_id,
            )
        )
        if not include_deleted:
            statement = statement.where(KnowledgeBase.deleted_at.is_(None))
        if status is not None:
            statement = statement.where(KnowledgeBase.status == status)
        if query:
            statement = statement.where(KnowledgeBase.name.ilike(f"%{query}%"))
        result = await self._session.scalar(statement)
        return int(result or 0)

    async def publish(
        self,
        entity: KnowledgeBase,
        *,
        updated_by_user_id: uuid.UUID,
    ) -> None:
        """Mark a knowledge base ``active`` (draft → published)."""
        entity.status = KnowledgeBaseStatus.ACTIVE
        entity.updated_by_user_id = updated_by_user_id
        entity.row_version += 1

    async def name_exists(
        self,
        scope: TenantScope,
        name: str,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        statement = (
            select(func.count())
            .select_from(KnowledgeBase)
            .where(
                KnowledgeBase.organization_id == scope.organization_id,
                KnowledgeBase.workspace_id == scope.workspace_id,
                KnowledgeBase.name == name.strip(),
                KnowledgeBase.deleted_at.is_(None),
                KnowledgeBase.status != KnowledgeBaseStatus.DELETED,
            )
        )
        if exclude_id is not None:
            statement = statement.where(KnowledgeBase.id != exclude_id)
        result = await self._session.scalar(statement)
        return bool(result)

    def _scoped_select(
        self,
        scope: TenantScope,
        *,
        include_deleted: bool,
    ) -> Select[tuple[KnowledgeBase]]:
        statement = select(KnowledgeBase).where(
            KnowledgeBase.organization_id == scope.organization_id,
            KnowledgeBase.workspace_id == scope.workspace_id,
        )
        if not include_deleted:
            statement = statement.where(KnowledgeBase.deleted_at.is_(None))
        return statement
