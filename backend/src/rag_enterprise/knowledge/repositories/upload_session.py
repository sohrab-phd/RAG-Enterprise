"""Upload session repository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import cast

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_enterprise.db.repositories.base import SQLAlchemyRepository
from rag_enterprise.db.result_utils import result_rowcount
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

    async def list_staging_keys_for_kb(self, knowledge_base_id: uuid.UUID) -> list[str]:
        statement = select(UploadSession.storage_key_staging).where(
            UploadSession.knowledge_base_id == knowledge_base_id,
            UploadSession.storage_key_staging.is_not(None),
        )
        rows = (await self._session.scalars(statement)).all()
        return [key for key in rows if key]

    async def list_staging_keys_for_document(self, document_id: uuid.UUID) -> list[str]:
        statement = select(UploadSession.storage_key_staging).where(
            UploadSession.document_id == document_id,
            UploadSession.storage_key_staging.is_not(None),
        )
        rows = (await self._session.scalars(statement)).all()
        return [key for key in rows if key]

    async def list_staging_keys_for_documents(self, document_ids: Sequence[uuid.UUID]) -> list[str]:
        if not document_ids:
            return []
        statement = select(UploadSession.storage_key_staging).where(
            UploadSession.document_id.in_(list(document_ids)),
            UploadSession.storage_key_staging.is_not(None),
        )
        rows = (await self._session.scalars(statement)).all()
        return [key for key in rows if key]

    async def delete_all_for_knowledge_base(self, knowledge_base_id: uuid.UUID) -> int:
        result = await self._session.execute(
            delete(UploadSession).where(UploadSession.knowledge_base_id == knowledge_base_id)
        )
        return result_rowcount(result)

    async def delete_all_for_document(self, document_id: uuid.UUID) -> int:
        result = await self._session.execute(
            delete(UploadSession).where(UploadSession.document_id == document_id)
        )
        return result_rowcount(result)

    async def delete_all_for_documents(self, document_ids: Sequence[uuid.UUID]) -> int:
        if not document_ids:
            return 0
        result = await self._session.execute(
            delete(UploadSession).where(UploadSession.document_id.in_(list(document_ids)))
        )
        return result_rowcount(result)
