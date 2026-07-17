"""Chunk repository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_enterprise.db.repositories.base import SQLAlchemyRepository
from rag_enterprise.indexing.enums import ChunkStatus
from rag_enterprise.indexing.models import Chunk


class ChunkRepository(SQLAlchemyRepository[Chunk]):
    """Persistence for chunk rows."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Chunk)

    async def list_for_version(self, document_version_id: uuid.UUID) -> Sequence[Chunk]:
        statement = (
            select(Chunk)
            .where(Chunk.document_version_id == document_version_id)
            .where(Chunk.status != ChunkStatus.DELETED)
            .order_by(Chunk.sequence_number.asc())
        )
        result = await self._session.scalars(statement)
        return result.all()

    async def get_many(self, chunk_ids: Sequence[uuid.UUID]) -> Sequence[Chunk]:
        if not chunk_ids:
            return []
        statement = select(Chunk).where(Chunk.id.in_(list(chunk_ids)))
        result = await self._session.scalars(statement)
        return result.all()

    async def mark_superseded_for_versions(
        self,
        document_version_ids: Sequence[uuid.UUID],
    ) -> None:
        if not document_version_ids:
            return
        statement = (
            update(Chunk)
            .where(Chunk.document_version_id.in_(list(document_version_ids)))
            .where(Chunk.status != ChunkStatus.DELETED)
            .values(status=ChunkStatus.SUPERSEDED)
        )
        await self._session.execute(statement)

    async def mark_indexed(self, chunk_ids: Sequence[uuid.UUID]) -> None:
        if not chunk_ids:
            return
        statement = (
            update(Chunk).where(Chunk.id.in_(list(chunk_ids))).values(status=ChunkStatus.INDEXED)
        )
        await self._session.execute(statement)

    async def get_by_id(self, chunk_id: uuid.UUID) -> Chunk | None:
        return await self.get(chunk_id)

    async def delete_all_for_knowledge_base(self, knowledge_base_id: uuid.UUID) -> int:
        result = await self._session.execute(
            delete(Chunk).where(Chunk.knowledge_base_id == knowledge_base_id)
        )
        return int(result.rowcount or 0)

    async def delete_all_for_document(self, document_id: uuid.UUID) -> int:
        result = await self._session.execute(
            delete(Chunk).where(Chunk.document_id == document_id)
        )
        return int(result.rowcount or 0)

    async def delete_all_for_documents(self, document_ids: Sequence[uuid.UUID]) -> int:
        if not document_ids:
            return 0
        result = await self._session.execute(
            delete(Chunk).where(Chunk.document_id.in_(list(document_ids)))
        )
        return int(result.rowcount or 0)
