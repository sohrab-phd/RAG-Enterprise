"""Embedding repository with cosine similarity search."""

from __future__ import annotations

import math
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Float, Select, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_enterprise.db.repositories.base import SQLAlchemyRepository
from rag_enterprise.indexing.enums import ChunkStatus, IndexStatus
from rag_enterprise.indexing.models import Chunk, Embedding
from rag_enterprise.knowledge.enums import DocumentStatus, ProcessingStatus
from rag_enterprise.knowledge.models import Document, DocumentVersion


@dataclass(frozen=True)
class VectorHit:
    """Raw vector search hit before ACL hydration."""

    embedding_id: uuid.UUID
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    score: float
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    heading: str | None
    language: str | None


class EmbeddingRepository(SQLAlchemyRepository[Embedding]):
    """Persistence and dense vector search for embeddings."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Embedding)

    async def find_active_match(
        self,
        *,
        chunk_id: uuid.UUID,
        embedding_model_id: uuid.UUID,
        content_hash: str,
    ) -> Embedding | None:
        statement = (
            select(Embedding)
            .where(Embedding.chunk_id == chunk_id)
            .where(Embedding.embedding_model_id == embedding_model_id)
            .where(Embedding.content_hash == content_hash)
            .where(Embedding.index_status == IndexStatus.INDEXED)
            .limit(1)
        )
        result = await self._session.scalar(statement)
        return result

    async def next_generation(
        self,
        *,
        chunk_id: uuid.UUID,
        embedding_model_id: uuid.UUID,
    ) -> int:
        statement = (
            select(Embedding.generation)
            .where(Embedding.chunk_id == chunk_id)
            .where(Embedding.embedding_model_id == embedding_model_id)
            .order_by(Embedding.generation.desc())
            .limit(1)
        )
        current = await self._session.scalar(statement)
        if current is None:
            return 1
        return int(current) + 1

    async def mark_stale_for_chunk_model(
        self,
        *,
        chunk_id: uuid.UUID,
        embedding_model_id: uuid.UUID,
    ) -> None:
        statement = (
            update(Embedding)
            .where(Embedding.chunk_id == chunk_id)
            .where(Embedding.embedding_model_id == embedding_model_id)
            .where(Embedding.index_status == IndexStatus.INDEXED)
            .values(index_status=IndexStatus.STALE)
        )
        await self._session.execute(statement)

    async def mark_stale_for_versions(
        self,
        document_version_ids: Sequence[uuid.UUID],
    ) -> None:
        if not document_version_ids:
            return
        statement = (
            update(Embedding)
            .where(Embedding.document_version_id.in_(list(document_version_ids)))
            .where(Embedding.index_status == IndexStatus.INDEXED)
            .values(index_status=IndexStatus.STALE)
        )
        await self._session.execute(statement)

    async def count_indexed_for_kb(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        embedding_model_id: uuid.UUID,
    ) -> int:
        from sqlalchemy import func

        statement = (
            select(func.count())
            .select_from(Embedding)
            .where(Embedding.organization_id == organization_id)
            .where(Embedding.knowledge_base_id == knowledge_base_id)
            .where(Embedding.embedding_model_id == embedding_model_id)
            .where(Embedding.index_status == IndexStatus.INDEXED)
        )
        result = await self._session.scalar(statement)
        return int(result or 0)

    async def search_cosine(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        embedding_model_id: uuid.UUID,
        query_vector: list[float],
        top_k: int,
        document_ids: Sequence[uuid.UUID] | None = None,
        language: str | None = None,
    ) -> list[VectorHit]:
        dialect = self._session.bind.dialect.name if self._session.bind is not None else "sqlite"
        if dialect == "postgresql":
            return await self._search_postgresql(
                organization_id=organization_id,
                knowledge_base_id=knowledge_base_id,
                embedding_model_id=embedding_model_id,
                query_vector=query_vector,
                top_k=top_k,
                document_ids=document_ids,
                language=language,
            )
        return await self._search_python(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            embedding_model_id=embedding_model_id,
            query_vector=query_vector,
            top_k=top_k,
            document_ids=document_ids,
            language=language,
        )

    def _filtered_join(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        embedding_model_id: uuid.UUID,
        document_ids: Sequence[uuid.UUID] | None,
        language: str | None,
    ) -> Select[tuple[Embedding, Chunk, Document]]:
        statement = (
            select(Embedding, Chunk, Document)
            .join(Chunk, Chunk.id == Embedding.chunk_id)
            .join(Document, Document.id == Chunk.document_id)
            .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
            .where(Embedding.organization_id == organization_id)
            .where(Embedding.knowledge_base_id == knowledge_base_id)
            .where(Embedding.embedding_model_id == embedding_model_id)
            .where(Embedding.index_status == IndexStatus.INDEXED)
            .where(Chunk.status == ChunkStatus.INDEXED)
            .where(DocumentVersion.processing_status == ProcessingStatus.INDEXED)
            .where(Document.status == DocumentStatus.ACTIVE)
            .where(Document.deleted_at.is_(None))
        )
        if document_ids:
            statement = statement.where(Chunk.document_id.in_(list(document_ids)))
        if language is not None:
            statement = statement.where(Chunk.language == language)
        return statement

    async def _search_postgresql(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        embedding_model_id: uuid.UUID,
        query_vector: list[float],
        top_k: int,
        document_ids: Sequence[uuid.UUID] | None,
        language: str | None,
    ) -> list[VectorHit]:
        # Keep distance as Float only. Do not compute `1 - distance` in SQL —
        # SQLAlchemy otherwise types the literal `1` as EmbeddingVector and fails
        # bind processing (chat/retrieve 500: TypeError int has no len()).
        distance = Embedding.vector.op("<=>", return_type=Float())(query_vector)
        statement = (
            self._filtered_join(
                organization_id=organization_id,
                knowledge_base_id=knowledge_base_id,
                embedding_model_id=embedding_model_id,
                document_ids=document_ids,
                language=language,
            )
            .add_columns(distance.label("distance"))
            .order_by(distance.asc(), Document.id.asc(), Chunk.sequence_number.asc())
            .limit(top_k)
        )
        rows = (await self._session.execute(statement)).all()
        hits: list[VectorHit] = []
        for embedding, chunk, document, distance_value in rows:
            score = 1.0 - float(distance_value)
            hits.append(
                VectorHit(
                    embedding_id=embedding.id,
                    chunk_id=chunk.id,
                    document_id=document.id,
                    document_version_id=chunk.document_version_id,
                    knowledge_base_id=chunk.knowledge_base_id,
                    score=max(0.0, min(1.0, score)),
                    text=chunk.text,
                    chunk_index=chunk.sequence_number,
                    start_char=chunk.start_offset,
                    end_char=chunk.end_offset,
                    heading=chunk.heading,
                    language=chunk.language,
                )
            )
        return hits

    async def _search_python(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        embedding_model_id: uuid.UUID,
        query_vector: list[float],
        top_k: int,
        document_ids: Sequence[uuid.UUID] | None,
        language: str | None,
    ) -> list[VectorHit]:
        statement = self._filtered_join(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            embedding_model_id=embedding_model_id,
            document_ids=document_ids,
            language=language,
        )
        rows = (await self._session.execute(statement)).all()
        scored: list[VectorHit] = []
        for embedding, chunk, document in rows:
            score = _cosine_similarity(query_vector, list(embedding.vector))
            scored.append(
                VectorHit(
                    embedding_id=embedding.id,
                    chunk_id=chunk.id,
                    document_id=document.id,
                    document_version_id=chunk.document_version_id,
                    knowledge_base_id=chunk.knowledge_base_id,
                    score=score,
                    text=chunk.text,
                    chunk_index=chunk.sequence_number,
                    start_char=chunk.start_offset,
                    end_char=chunk.end_offset,
                    heading=chunk.heading,
                    language=chunk.language,
                )
            )
        scored.sort(key=lambda hit: (-hit.score, hit.document_id.hex, hit.chunk_index))
        return scored[:top_k]

    async def delete_all_for_knowledge_base(self, knowledge_base_id: uuid.UUID) -> int:
        result = await self._session.execute(
            delete(Embedding).where(Embedding.knowledge_base_id == knowledge_base_id)
        )
        return int(result.rowcount or 0)

    async def delete_all_for_document(self, document_id: uuid.UUID) -> int:
        chunk_ids = select(Chunk.id).where(Chunk.document_id == document_id)
        result = await self._session.execute(
            delete(Embedding).where(Embedding.chunk_id.in_(chunk_ids))
        )
        return int(result.rowcount or 0)


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (left_norm * right_norm)))
