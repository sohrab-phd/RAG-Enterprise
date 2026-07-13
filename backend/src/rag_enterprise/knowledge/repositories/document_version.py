"""Document version repository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import cast

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_enterprise.db.repositories.base import SQLAlchemyRepository
from rag_enterprise.knowledge.models import DocumentVersion
from rag_enterprise.knowledge.repositories.scope import TenantScope


class DocumentVersionRepository(SQLAlchemyRepository[DocumentVersion]):
    """Persistence access for document versions."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, DocumentVersion)

    async def get_scoped(
        self,
        scope: TenantScope,
        knowledge_base_id: uuid.UUID,
        document_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> DocumentVersion | None:
        statement = self._scoped_select(scope, knowledge_base_id).where(
            DocumentVersion.id == version_id,
            DocumentVersion.document_id == document_id,
        )
        return cast(DocumentVersion | None, await self._session.scalar(statement))

    async def list_for_document(
        self,
        scope: TenantScope,
        knowledge_base_id: uuid.UUID,
        document_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> Sequence[DocumentVersion]:
        statement = (
            self._scoped_select(scope, knowledge_base_id)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
            .offset(offset)
        )
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.scalars(statement)
        return result.all()

    async def next_version_number(self, document_id: uuid.UUID) -> int:
        statement = select(func.max(DocumentVersion.version_number)).where(
            DocumentVersion.document_id == document_id
        )
        current = await self._session.scalar(statement)
        return int(current or 0) + 1

    async def get_by_upload_session(
        self,
        upload_session_id: uuid.UUID,
    ) -> DocumentVersion | None:
        statement = select(DocumentVersion).where(
            DocumentVersion.upload_session_id == upload_session_id
        )
        return cast(DocumentVersion | None, await self._session.scalar(statement))

    def _scoped_select(
        self,
        scope: TenantScope,
        knowledge_base_id: uuid.UUID,
    ) -> Select[tuple[DocumentVersion]]:
        return select(DocumentVersion).where(
            DocumentVersion.organization_id == scope.organization_id,
            DocumentVersion.workspace_id == scope.workspace_id,
            DocumentVersion.knowledge_base_id == knowledge_base_id,
        )
