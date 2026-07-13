"""Upload session repository."""

from __future__ import annotations

import uuid

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_enterprise.db.repositories.base import SQLAlchemyRepository
from rag_enterprise.knowledge.models import UploadSession
from rag_enterprise.knowledge.repositories.scope import TenantScope


class UploadSessionRepository(SQLAlchemyRepository[UploadSession]):
    """Persistence access for upload sessions."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UploadSession)

    async def get_scoped(
        self,
        scope: TenantScope,
        knowledge_base_id: uuid.UUID,
        upload_id: uuid.UUID,
    ) -> UploadSession | None:
        statement = select(UploadSession).where(
            UploadSession.organization_id == scope.organization_id,
            UploadSession.workspace_id == scope.workspace_id,
            UploadSession.knowledge_base_id == knowledge_base_id,
            UploadSession.id == upload_id,
        )
        return cast(UploadSession | None, await self._session.scalar(statement))
