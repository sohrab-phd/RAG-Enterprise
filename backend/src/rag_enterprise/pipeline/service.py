"""Synchronous process → chunk → index orchestration (RC1.6)."""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.application.interfaces.file_storage import FileStorage
from rag_enterprise.chunking.service import ChunkingError, ChunkingResult, ChunkingService
from rag_enterprise.indexing.exceptions import IndexingError
from rag_enterprise.indexing.models import Chunk, Embedding
from rag_enterprise.indexing.service import IndexingService
from rag_enterprise.knowledge.enums import DocumentStatus, ProcessingStatus
from rag_enterprise.knowledge.models import Document, DocumentVersion
from rag_enterprise.processing.exceptions import ProcessingError
from rag_enterprise.processing.service import DocumentProcessingService


@dataclass(frozen=True)
class ProcessAndIndexResult:
    """Operator-facing outcome of a synchronous process-and-index run."""

    current_status: str
    processed_chunks: int
    indexed_embeddings: int
    warnings: list[str] = field(default_factory=list)
    document_version_id: uuid.UUID | None = None
    failure_reason: str | None = None


class ProcessAndIndexError(Exception):
    """Structured orchestration failure (HTTP layer maps to ApplicationException)."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        current_status: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.current_status = current_status
        self.details = details or {}
        super().__init__(message)


class ProcessAndIndexService:
    """Run uploaded → processing → chunking → embedding → indexed synchronously."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        file_storage: FileStorage,
        processing_service: DocumentProcessingService,
        chunking_service: ChunkingService,
        indexing_service: IndexingService,
    ) -> None:
        self._session_factory = session_factory
        self._file_storage = file_storage
        self._processing = processing_service
        self._chunking = chunking_service
        self._indexing = indexing_service

    async def process_document(
        self,
        *,
        organization_id: uuid.UUID,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> ProcessAndIndexResult:
        """Process the document's current version end-to-end."""
        warnings: list[str] = []
        version_id, status = await self._load_version(
            organization_id=organization_id,
            workspace_id=workspace_id,
            document_id=document_id,
        )

        if status == ProcessingStatus.INDEXED:
            chunks, embeddings = await self._count_artifacts(version_id)
            return ProcessAndIndexResult(
                current_status=ProcessingStatus.INDEXED,
                processed_chunks=chunks,
                indexed_embeddings=embeddings,
                warnings=["already_indexed"],
                document_version_id=version_id,
            )

        if status not in {
            ProcessingStatus.UPLOADED,
            ProcessingStatus.FAILED,
            ProcessingStatus.EXTRACTED,
            ProcessingStatus.CHUNKED,
        }:
            raise ProcessAndIndexError(
                "conflict",
                f"Document version cannot be processed from status {status}",
                current_status=status,
                details={"document_version_id": str(version_id)},
            )

        try:
            chunk_language: str | None = None
            if status in {ProcessingStatus.UPLOADED, ProcessingStatus.FAILED}:
                extract_warnings, chunk_language = await self._run_processing(version_id)
                warnings.extend(extract_warnings)
                status = ProcessingStatus.EXTRACTED

            if status == ProcessingStatus.EXTRACTED:
                chunk_result = await self._run_chunking(
                    version_id,
                    language=chunk_language,
                )
                warnings.extend(list(chunk_result.warnings))
                processed_chunks = chunk_result.chunk_count
            else:
                processed_chunks, _ = await self._count_artifacts(version_id)

            index_result = await self._indexing.index_document_version(version_id)
            warnings.extend(index_result.warnings)
            _, embeddings = await self._count_artifacts(version_id)
            return ProcessAndIndexResult(
                current_status=ProcessingStatus.INDEXED,
                processed_chunks=processed_chunks,
                indexed_embeddings=embeddings,
                warnings=warnings,
                document_version_id=version_id,
            )
        except ProcessAndIndexError:
            raise
        except (ProcessingError, ChunkingError, IndexingError, OSError, KeyError) as exc:
            failed_status = await self._mark_failed(version_id, exc)
            raise ProcessAndIndexError(
                "internal_error",
                str(exc),
                current_status=failed_status,
                details={
                    "document_version_id": str(version_id),
                    "failure_code": str(getattr(exc, "code", type(exc).__name__)),
                },
            ) from exc

    async def _load_version(
        self,
        *,
        organization_id: uuid.UUID,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> tuple[uuid.UUID, str]:
        async with self._session_factory() as session:
            document = await session.scalar(
                select(Document).where(
                    Document.id == document_id,
                    Document.organization_id == organization_id,
                    Document.workspace_id == workspace_id,
                    Document.status != DocumentStatus.DELETED,
                )
            )
            if document is None:
                raise ProcessAndIndexError("not_found", "Document not found")
            if document.current_version_id is None:
                raise ProcessAndIndexError(
                    "conflict",
                    "Document has no current version to process",
                )
            version = await session.get(DocumentVersion, document.current_version_id)
            if version is None:
                raise ProcessAndIndexError("not_found", "Document version not found")
            return version.id, version.processing_status

    async def _run_processing(self, version_id: uuid.UUID) -> tuple[list[str], str | None]:
        async with self._session_factory() as session:
            version = await session.get(DocumentVersion, version_id)
            if version is None:
                raise ProcessAndIndexError("not_found", "Document version not found")
            version.processing_status = ProcessingStatus.EXTRACTING
            version.failure_reason = None
            await session.commit()
            organization_id = version.organization_id
            workspace_id = version.workspace_id
            storage_key = version.storage_key_original
            file_name = version.file_name
            document = await session.get(Document, version.document_id)
            declared_language = document.declared_language if document is not None else None

        original_bytes = await self._file_storage.get(key=storage_key)
        suffix = Path(file_name).suffix or ".txt"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(original_bytes)
            temp_path = Path(handle.name)
        try:
            extraction = await asyncio.to_thread(self._processing.process_file, temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

        extracted_key = f"{storage_key}.extracted.txt"
        await self._file_storage.put(
            organization_id=organization_id,
            workspace_id=workspace_id,
            key=extracted_key,
            data=extraction.text.encode("utf-8"),
            content_type="text/plain; charset=utf-8",
        )

        async with self._session_factory() as session:
            version = await session.get(DocumentVersion, version_id)
            if version is None:
                raise ProcessAndIndexError("not_found", "Document version not found")
            version.storage_key_extracted = extracted_key
            version.processing_status = ProcessingStatus.EXTRACTED
            version.failure_reason = None
            await session.commit()

        detected = extraction.metadata.language
        if detected and detected != "unknown":
            language: str | None = detected
        else:
            language = declared_language
        return list(extraction.warnings), language

    async def _run_chunking(
        self,
        version_id: uuid.UUID,
        *,
        language: str | None,
    ) -> ChunkingResult:
        async with self._session_factory() as session:
            version = await session.get(DocumentVersion, version_id)
            if version is None:
                raise ProcessAndIndexError("not_found", "Document version not found")
            if not version.storage_key_extracted:
                raise ProcessAndIndexError(
                    "conflict",
                    "Document version has no extracted text",
                    current_status=version.processing_status,
                )
            extracted_key = version.storage_key_extracted
            if language is None:
                document = await session.get(Document, version.document_id)
                language = document.declared_language if document is not None else None

        text_bytes = await self._file_storage.get(key=extracted_key)
        text = text_bytes.decode("utf-8")
        return await self._chunking.chunk_document_version(
            document_version_id=version_id,
            text=text,
            language=language,
        )

    async def _mark_failed(self, version_id: uuid.UUID, exc: Exception) -> str:
        reason = getattr(exc, "code", None) or type(exc).__name__
        message = str(exc)[:500]
        async with self._session_factory() as session:
            version = await session.get(DocumentVersion, version_id)
            if version is None:
                return ProcessingStatus.FAILED
            # IndexingService may already persist FAILED; keep that if present.
            if version.processing_status != ProcessingStatus.FAILED:
                version.processing_status = ProcessingStatus.FAILED
                version.failure_reason = f"{reason}: {message}"
                await session.commit()
            return version.processing_status

    async def _count_artifacts(self, version_id: uuid.UUID) -> tuple[int, int]:
        async with self._session_factory() as session:
            chunks = await session.scalar(
                select(func.count())
                .select_from(Chunk)
                .where(Chunk.document_version_id == version_id)
            )
            embeddings = await session.scalar(
                select(func.count())
                .select_from(Embedding)
                .where(Embedding.document_version_id == version_id)
            )
        return int(chunks or 0), int(embeddings or 0)
