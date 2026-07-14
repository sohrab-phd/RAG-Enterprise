"""Paragraph-aware chunk generation for document versions."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.indexing.enums import ChunkStatus
from rag_enterprise.indexing.models import Chunk, Embedding
from rag_enterprise.knowledge.enums import ProcessingStatus
from rag_enterprise.knowledge.models import DocumentVersion

_BLANK_LINE_RE = re.compile(r"\n\s*\n+")

DEFAULT_MAX_CHUNK_CHARS = 1200
DEFAULT_MIN_CHUNK_CHARS = 50


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
    """Create Chunk rows from extracted text (paragraph-aware strategy)."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
        min_chunk_chars: int = DEFAULT_MIN_CHUNK_CHARS,
    ) -> None:
        self._session_factory = session_factory
        self._max_chunk_chars = max_chunk_chars
        self._min_chunk_chars = min_chunk_chars

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

        segments = self._split_paragraphs(cleaned)
        warnings: list[str] = []
        if len(segments) == 1 and len(cleaned) > self._max_chunk_chars:
            warnings.append("oversized_paragraph_split")

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

            chunks = self._build_chunks(
                version=version,
                text=cleaned,
                language=language,
                segments=segments,
            )
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

    def _split_paragraphs(self, text: str) -> list[str]:
        parts = [part.strip() for part in _BLANK_LINE_RE.split(text) if part.strip()]
        return parts if parts else [text]

    def _build_chunks(
        self,
        *,
        version: DocumentVersion,
        text: str,
        language: str | None,
        segments: list[str],
    ) -> list[Chunk]:
        bodies = self._merge_segments(segments)
        chunks: list[Chunk] = []
        search_from = 0
        for index, body in enumerate(bodies):
            start = text.find(body, search_from)
            if start < 0:
                start = search_from
            end = start + len(body)
            search_from = end
            chunks.append(
                Chunk(
                    organization_id=version.organization_id,
                    workspace_id=version.workspace_id,
                    knowledge_base_id=version.knowledge_base_id,
                    document_id=version.document_id,
                    document_version_id=version.id,
                    sequence_number=index,
                    text=body,
                    content_hash=hashlib.sha256(body.encode("utf-8")).hexdigest(),
                    start_offset=start,
                    end_offset=end,
                    language=language,
                    strategy="paragraph",
                    status=ChunkStatus.CREATED,
                )
            )
        return chunks

    def _merge_segments(self, segments: list[str]) -> list[str]:
        merged: list[str] = []
        buffer = ""
        for segment in segments:
            pieces = self._split_oversized(segment)
            for piece in pieces:
                candidate = f"{buffer}\n\n{piece}".strip() if buffer else piece
                if buffer and len(candidate) > self._max_chunk_chars:
                    if len(buffer) >= self._min_chunk_chars or not merged:
                        merged.append(buffer)
                    else:
                        merged[-1] = f"{merged[-1]}\n\n{buffer}".strip()
                    buffer = piece
                else:
                    buffer = candidate
        if buffer:
            if (
                merged
                and len(buffer) < self._min_chunk_chars
                and len(f"{merged[-1]}\n\n{buffer}") <= self._max_chunk_chars
            ):
                merged[-1] = f"{merged[-1]}\n\n{buffer}".strip()
            else:
                merged.append(buffer)
        return merged or segments[:1]

    def _split_oversized(self, paragraph: str) -> list[str]:
        if len(paragraph) <= self._max_chunk_chars:
            return [paragraph]
        parts: list[str] = []
        remaining = paragraph
        while len(remaining) > self._max_chunk_chars:
            window = remaining[: self._max_chunk_chars]
            split_at = max(window.rfind(". "), window.rfind(" "), window.rfind("\n"))
            if split_at < int(self._max_chunk_chars * 0.5):
                split_at = self._max_chunk_chars
            else:
                split_at += 1
            parts.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()
        if remaining:
            parts.append(remaining)
        return [part for part in parts if part]
