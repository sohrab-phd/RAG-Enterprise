"""Bridge uploaded document versions through process → chunk → index.

HTTP APIs stop at ``processing_status=uploaded``. Until a worker exposes those
stages, the RC1.3 golden path calls real application services in-process:

- ``DocumentProcessingService`` for extraction/normalization
- ORM chunk rows (Feature 003 HTTP chunker not shipped)
- ``IndexingService`` for embeddings + ``indexed`` status

No business services are mocked.
"""

from __future__ import annotations

import asyncio
import hashlib
import tempfile
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.application.interfaces.file_storage import FileStorage
from rag_enterprise.indexing.enums import ChunkStatus
from rag_enterprise.indexing.models import Chunk
from rag_enterprise.indexing.service import IndexingService
from rag_enterprise.knowledge.enums import ProcessingStatus
from rag_enterprise.knowledge.models import DocumentVersion
from rag_enterprise.processing.service import DocumentProcessingService


async def advance_uploaded_version_to_indexed(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    file_storage: FileStorage,
    indexing_service: IndexingService,
    document_version_id: uuid.UUID,
    organization_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> uuid.UUID:
    """Extract, create a single retrieval chunk, embed, and mark the version indexed.

    Returns the created chunk id (used for citation/evaluation expectations).
    """
    processor = DocumentProcessingService()

    async with session_factory() as session:
        version = await session.get(DocumentVersion, document_version_id)
        if version is None:
            raise RuntimeError(f"document version not found: {document_version_id}")
        if version.processing_status != ProcessingStatus.UPLOADED:
            raise RuntimeError(f"expected uploaded status, got {version.processing_status}")

        original_bytes = await file_storage.get(key=version.storage_key_original)
        suffix = Path(version.file_name).suffix or ".txt"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(original_bytes)
            temp_path = Path(handle.name)

        try:
            extraction = await asyncio.to_thread(processor.process_file, temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

        extracted_key = f"{version.storage_key_original}.extracted.txt"
        await file_storage.put(
            organization_id=organization_id,
            workspace_id=workspace_id,
            key=extracted_key,
            data=extraction.text.encode("utf-8"),
            content_type="text/plain; charset=utf-8",
        )

        version.processing_status = ProcessingStatus.EXTRACTED
        version.storage_key_extracted = extracted_key
        await session.flush()

        text = extraction.text.strip()
        chunk = Chunk(
            organization_id=organization_id,
            workspace_id=workspace_id,
            knowledge_base_id=version.knowledge_base_id,
            document_id=version.document_id,
            document_version_id=version.id,
            sequence_number=0,
            text=text,
            content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            start_offset=0,
            end_offset=len(text),
            language=extraction.metadata.language
            if extraction.metadata.language != "unknown"
            else "fa",
            strategy="document",
            status=ChunkStatus.CREATED,
        )
        session.add(chunk)
        version.processing_status = ProcessingStatus.CHUNKED
        await session.commit()
        await session.refresh(chunk)
        chunk_id = chunk.id

    result = await indexing_service.index_document_version(document_version_id)
    if result.embeddings_failed:
        raise RuntimeError(f"indexing reported failures: {result.embeddings_failed}")

    async with session_factory() as session:
        version = await session.get(DocumentVersion, document_version_id)
        if version is None or version.processing_status != ProcessingStatus.INDEXED:
            status = None if version is None else version.processing_status
            raise RuntimeError(f"version not indexed after pipeline, status={status}")

    return chunk_id
