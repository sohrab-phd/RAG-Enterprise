"""Paragraph-aware chunk generation for document versions."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.chunking.splitter import (
    DEFAULT_MAX_CHUNK_CHARS,
    DEFAULT_MIN_CHUNK_CHARS,
    DEFAULT_OVERLAP_CHARS,
    DEFAULT_TARGET_CHUNK_CHARS,
    split_persian_document,
)
from rag_enterprise.indexing.enums import ChunkStatus
from rag_enterprise.indexing.models import Chunk, Embedding
from rag_enterprise.knowledge.enums import ProcessingStatus
from rag_enterprise.knowledge.models import DocumentVersion


@dataclass(frozen=True)
class ChunkingResult:
    """Outcome of chunking a document version."""

    document_version_id: uuid.UUID
    chunk_count: int
    warnings: tuple[str, ...] = ()


class ChunkingError(Exception):
    """Raised when chunking cannot complete."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class ChunkingService:
    """Create Chunk rows from extracted text (Persian-aware paragraph/heading strategy)."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
        min_chunk_chars: int = DEFAULT_MIN_CHUNK_CHARS,
        overlap_chars: int = DEFAULT_OVERLAP_CHARS,
        target_chunk_chars: int = DEFAULT_TARGET_CHUNK_CHARS,
    ) -> None:
        self._session_factory = session_factory
        self._max_chunk_chars = max_chunk_chars
        self._min_chunk_chars = min_chunk_chars
        self._overlap_chars = overlap_chars
        self._target_chunk_chars = target_chunk_chars

    async def chunk_document_version(
        self,
        *,
        document_version_id: uuid.UUID,
        text: str,
        language: str | None,
    ) -> ChunkingResult:
        """Replace chunks for a version and mark it ``chunked``."""
        cleaned = text.strip()
        if not cleaned:
            raise ChunkingError("empty_content", "Extracted text is empty")

        pieces = split_persian_document(
            cleaned,
            max_chunk_chars=self._max_chunk_chars,
            min_chunk_chars=self._min_chunk_chars,
            overlap_chars=self._overlap_chars,
            target_chunk_chars=self._target_chunk_chars,
        )
        warnings: list[str] = []
        if any(piece.overlap_chars for piece in pieces):
            warnings.append("oversized_unit_split_with_overlap")
        if any(piece.strategy == "heading" for piece in pieces):
            warnings.append("heading_boundaries_applied")
        else:
            warnings.append("paragraph_boundaries_applied")

        async with self._session_factory() as session:
            version = await session.get(DocumentVersion, document_version_id)
            if version is None:
                raise ChunkingError("not_found", f"Version not found: {document_version_id}")

            version.processing_status = ProcessingStatus.CHUNKING
            version.failure_reason = None
            await session.flush()

            await session.execute(
                delete(Embedding).where(Embedding.document_version_id == document_version_id)
            )
            await session.execute(
                delete(Chunk).where(Chunk.document_version_id == document_version_id)
            )

            chunks = [
                Chunk(
                    organization_id=version.organization_id,
                    workspace_id=version.workspace_id,
                    knowledge_base_id=version.knowledge_base_id,
                    document_id=version.document_id,
                    document_version_id=version.id,
                    sequence_number=index,
                    text=piece.text,
                    content_hash=hashlib.sha256(piece.text.encode("utf-8")).hexdigest(),
                    start_offset=piece.start,
                    end_offset=piece.end,
                    heading=piece.heading,
                    language=language,
                    strategy=piece.strategy,
                    status=ChunkStatus.CREATED,
                )
                for index, piece in enumerate(pieces)
            ]
            if not chunks:
                version.processing_status = ProcessingStatus.FAILED
                version.failure_reason = "empty_chunk_list"
                await session.commit()
                raise ChunkingError("empty_chunk_list", "No chunks produced from extracted text")

            session.add_all(chunks)
            version.processing_status = ProcessingStatus.CHUNKED
            await session.commit()

        return ChunkingResult(
            document_version_id=document_version_id,
            chunk_count=len(chunks),
            warnings=tuple(warnings),
        )
