"""Load indexed Persian chunks from the live knowledge base (read-only)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.indexing.enums import ChunkStatus
from rag_enterprise.indexing.models import Chunk
from rag_enterprise.knowledge.enums import DocumentStatus
from rag_enterprise.knowledge.models import Document
from tools.persian_rag_benchmark.models import ChunkSnapshot


async def load_kb_chunks(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    organization_id: uuid.UUID,
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    document_ids: tuple[uuid.UUID, ...] = (),
) -> list[ChunkSnapshot]:
    """Return active chunks for a knowledge base, optionally filtered by documents."""
    async with session_factory() as session:
        statement = (
            select(Chunk, Document.title)
            .join(Document, Document.id == Chunk.document_id)
            .where(
                Chunk.organization_id == organization_id,
                Chunk.workspace_id == workspace_id,
                Chunk.knowledge_base_id == knowledge_base_id,
                Chunk.status != ChunkStatus.DELETED,
                Document.status != DocumentStatus.DELETED,
            )
            .order_by(Document.id.asc(), Chunk.sequence_number.asc())
        )
        if document_ids:
            statement = statement.where(Chunk.document_id.in_(document_ids))

        rows = (await session.execute(statement)).all()

    snapshots: list[ChunkSnapshot] = []
    for chunk, title in rows:
        snapshots.append(
            ChunkSnapshot(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_version_id=chunk.document_version_id,
                knowledge_base_id=chunk.knowledge_base_id,
                sequence_number=chunk.sequence_number,
                text=chunk.text,
                language=chunk.language,
                heading=chunk.heading,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
                document_title=title,
            )
        )
    return snapshots
