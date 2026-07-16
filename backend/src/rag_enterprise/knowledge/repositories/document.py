"""Document repository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import cast

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_enterprise.db.repositories.base import SQLAlchemyRepository
from rag_enterprise.knowledge.enums import DocumentStatus
from rag_enterprise.knowledge.models import Document
from rag_enterprise.knowledge.repositories.scope import TenantScope


class DocumentRepository(SQLAlchemyRepository[Document]):
    """Persistence access for documents."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Document)

    async def get_scoped(
        self,
        scope: TenantScope,
        knowledge_base_id: uuid.UUID,
        document_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> Document | None:
        statement = self._scoped_select(
            scope,
            knowledge_base_id,
            include_deleted=include_deleted,
        ).where(Document.id == document_id)
        return cast(Document | None, await self._session.scalar(statement))

    async def list_in_folder(
        self,
        scope: TenantScope,
        knowledge_base_id: uuid.UUID,
        *,
        folder_id: uuid.UUID | None = None,
        status: str | None = None,
        declared_language: str | None = None,
        query: str | None = None,
        offset: int = 0,
        limit: int | None = None,
        include_deleted: bool = False,
    ) -> Sequence[Document]:
        statement = self._scoped_select(
            scope,
            knowledge_base_id,
            include_deleted=include_deleted,
        )
        if folder_id is None:
            statement = statement.where(Document.folder_id.is_(None))
        else:
            statement = statement.where(Document.folder_id == folder_id)
        if status is not None:
            statement = statement.where(Document.status == status)
        if declared_language is not None:
            statement = statement.where(Document.declared_language == declared_language)
        if query:
            statement = statement.where(Document.title.ilike(f"%{query}%"))
        statement = statement.order_by(Document.updated_at.desc()).offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.scalars(statement)
        return result.all()

    async def count_in_folder(
        self,
        scope: TenantScope,
        knowledge_base_id: uuid.UUID,
        *,
        folder_id: uuid.UUID | None = None,
        status: str | None = None,
        declared_language: str | None = None,
        query: str | None = None,
        include_deleted: bool = False,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(Document)
            .where(
                Document.organization_id == scope.organization_id,
                Document.workspace_id == scope.workspace_id,
                Document.knowledge_base_id == knowledge_base_id,
            )
        )
        if not include_deleted:
            statement = statement.where(Document.deleted_at.is_(None))
        if folder_id is None:
            statement = statement.where(Document.folder_id.is_(None))
        else:
            statement = statement.where(Document.folder_id == folder_id)
        if status is not None:
            statement = statement.where(Document.status == status)
        if declared_language is not None:
            statement = statement.where(Document.declared_language == declared_language)
        if query:
            statement = statement.where(Document.title.ilike(f"%{query}%"))
        result = await self._session.scalar(statement)
        return int(result or 0)

    async def search_metadata(
        self,
        scope: TenantScope,
        knowledge_base_id: uuid.UUID,
        *,
        query: str,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[Document]:
        pattern = f"%{query}%"
        statement = (
            self._scoped_select(scope, knowledge_base_id, include_deleted=False)
            .where(Document.title.ilike(pattern))
            .order_by(Document.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.scalars(statement)
        return result.all()

    async def archive_all_in_kb(self, knowledge_base_id: uuid.UUID) -> None:
        from datetime import UTC, datetime

        from sqlalchemy import update

        await self._session.execute(
            update(Document)
            .where(
                Document.knowledge_base_id == knowledge_base_id,
                Document.deleted_at.is_(None),
                Document.status.in_([DocumentStatus.DRAFT, DocumentStatus.ACTIVE]),
            )
            .values(status=DocumentStatus.ARCHIVED, archived_at=datetime.now(UTC))
        )

    async def soft_delete_all_in_kb(self, knowledge_base_id: uuid.UUID, user_id: uuid.UUID) -> None:
        from datetime import UTC, datetime

        from sqlalchemy import update

        now = datetime.now(UTC)
        await self._session.execute(
            update(Document)
            .where(Document.knowledge_base_id == knowledge_base_id, Document.deleted_at.is_(None))
            .values(
                status=DocumentStatus.DELETED,
                deleted_at=now,
                deleted_by_user_id=user_id,
            )
        )

    async def has_legal_hold_in_kb(self, knowledge_base_id: uuid.UUID) -> bool:
        statement = (
            select(func.count())
            .select_from(Document)
            .where(
                Document.knowledge_base_id == knowledge_base_id,
                Document.legal_hold.is_(True),
            )
        )
        result = await self._session.scalar(statement)
        return bool(result)

    async def hard_delete_all_in_kb(self, knowledge_base_id: uuid.UUID) -> int:
        result = await self._session.execute(
            delete(Document).where(Document.knowledge_base_id == knowledge_base_id)
        )
        return int(result.rowcount or 0)

    def _scoped_select(
        self,
        scope: TenantScope,
        knowledge_base_id: uuid.UUID,
        *,
        include_deleted: bool,
    ) -> Select[tuple[Document]]:
        statement = select(Document).where(
            Document.organization_id == scope.organization_id,
            Document.workspace_id == scope.workspace_id,
            Document.knowledge_base_id == knowledge_base_id,
        )
        if not include_deleted:
            statement = statement.where(Document.deleted_at.is_(None))
        return statement
