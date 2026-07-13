"""Document version indexing service."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.application.interfaces.embedding import EmbeddingProvider
from rag_enterprise.indexing.constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_BATCH_TIMEOUT_SECONDS,
    DEFAULT_EMBEDDING_MODEL_ID,
    DEFAULT_MAX_BATCH_CHARS,
)
from rag_enterprise.indexing.enums import ChunkStatus, IndexStatus
from rag_enterprise.indexing.exceptions import (
    DimensionMismatchError,
    EmbeddingTimeoutError,
    EmptyChunkListError,
    IndexingError,
    ModelUnavailableError,
    PartialEmbeddingFailureError,
    StorageWriteError,
)
from rag_enterprise.indexing.models import Chunk, Embedding, IndexingResult
from rag_enterprise.indexing.repositories import ChunkRepository, EmbeddingRepository
from rag_enterprise.knowledge.enums import ProcessingStatus
from rag_enterprise.knowledge.models import DocumentVersion
from rag_enterprise.knowledge.repositories.document_version import DocumentVersionRepository
from rag_enterprise.knowledge.repositories.scope import TenantScope

logger = logging.getLogger(__name__)


class IndexingService:
    """Embed chunks and persist vectors for a document version."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        embedding_provider: EmbeddingProvider,
        embedding_model_id: uuid.UUID = DEFAULT_EMBEDDING_MODEL_ID,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_batch_chars: int = DEFAULT_MAX_BATCH_CHARS,
        batch_timeout_seconds: float = DEFAULT_BATCH_TIMEOUT_SECONDS,
        retry_delays_seconds: Sequence[float] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._provider = embedding_provider
        self._embedding_model_id = embedding_model_id
        self._batch_size = batch_size
        self._max_batch_chars = max_batch_chars
        self._batch_timeout_seconds = batch_timeout_seconds
        self._retry_delays_seconds = list(retry_delays_seconds or (0.0, 0.0, 0.0))

    async def index_document_version(
        self,
        document_version_id: uuid.UUID,
    ) -> IndexingResult:
        """Index chunks for a chunked (or resume from failed/indexing) version."""
        return await self._run_with_retries(document_version_id, force=False)

    async def reindex_document_version(
        self,
        document_version_id: uuid.UUID,
    ) -> IndexingResult:
        """Force re-embedding of all chunks for a version."""
        return await self._run_with_retries(document_version_id, force=True)

    async def resume_failed_indexing(
        self,
        document_version_id: uuid.UUID,
    ) -> IndexingResult:
        """Resume indexing after failure; skips already-persisted embeddings."""
        async with self._session_factory() as session:
            versions = DocumentVersionRepository(session)
            version = await versions.get(document_version_id)
            if version is None:
                raise IndexingError("unknown_error", f"Version not found: {document_version_id}")
            if version.processing_status not in {
                ProcessingStatus.FAILED,
                ProcessingStatus.INDEXING,
                ProcessingStatus.CHUNKED,
            }:
                raise IndexingError(
                    "unknown_error",
                    f"Cannot resume from status {version.processing_status}",
                )
            if version.processing_status == ProcessingStatus.FAILED:
                version.processing_status = ProcessingStatus.CHUNKED
                version.failure_reason = None
                await session.commit()
        return await self.index_document_version(document_version_id)

    async def _run_with_retries(
        self,
        document_version_id: uuid.UUID,
        *,
        force: bool,
    ) -> IndexingResult:
        last_error: Exception | None = None
        attempts = max(1, len(self._retry_delays_seconds) + 1)
        for attempt in range(attempts):
            try:
                return await self._index_once(document_version_id, force=force)
            except IndexingError as exc:
                last_error = exc
                if exc.code in {"empty_chunk_list", "dimension_mismatch"}:
                    await self._mark_failed(document_version_id, exc.code)
                    raise
                if attempt >= attempts - 1:
                    await self._mark_failed(document_version_id, exc.code)
                    raise
                delay = self._retry_delays_seconds[attempt]
                if delay > 0:
                    await asyncio.sleep(delay)
            except Exception as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    await self._mark_failed(document_version_id, "unknown_error")
                    raise IndexingError("unknown_error", str(exc)) from exc
                delay = self._retry_delays_seconds[attempt]
                if delay > 0:
                    await asyncio.sleep(delay)
        assert last_error is not None
        raise last_error

    async def _index_once(
        self,
        document_version_id: uuid.UUID,
        *,
        force: bool,
    ) -> IndexingResult:
        async with self._session_factory() as session:
            versions = DocumentVersionRepository(session)
            chunks_repo = ChunkRepository(session)
            embeddings_repo = EmbeddingRepository(session)

            version = await versions.get(document_version_id)
            if version is None:
                raise IndexingError("unknown_error", f"Version not found: {document_version_id}")

            if version.processing_status == ProcessingStatus.INDEXED and not force:
                already_indexed = await chunks_repo.list_for_version(document_version_id)
                return IndexingResult(
                    document_version_id=document_version_id,
                    embedding_model_id=self._embedding_model_id,
                    embeddings_created=0,
                    embeddings_skipped=len(already_indexed),
                    embeddings_failed=0,
                )

            if version.processing_status not in {
                ProcessingStatus.CHUNKED,
                ProcessingStatus.INDEXING,
                ProcessingStatus.FAILED,
                ProcessingStatus.INDEXED,
            }:
                raise IndexingError(
                    "unknown_error",
                    f"Version status {version.processing_status} is not indexable",
                )

            version.processing_status = ProcessingStatus.INDEXING
            version.failure_reason = None
            await session.flush()

            chunks = list(await chunks_repo.list_for_version(document_version_id))
            if not chunks:
                version.processing_status = ProcessingStatus.FAILED
                version.failure_reason = "empty_chunk_list"
                await session.commit()
                raise EmptyChunkListError()

            logger.info(
                "indexing_started",
                extra={
                    "document_version_id": str(document_version_id),
                    "embedding_model_id": str(self._embedding_model_id),
                    "chunk_count": len(chunks),
                },
            )

            created = 0
            skipped = 0
            failed = 0
            warnings: list[str] = []
            pending: list[Chunk] = []

            for chunk in chunks:
                if not force:
                    existing = await embeddings_repo.find_active_match(
                        chunk_id=chunk.id,
                        embedding_model_id=self._embedding_model_id,
                        content_hash=chunk.content_hash,
                    )
                    if existing is not None:
                        skipped += 1
                        if chunk.status != ChunkStatus.INDEXED:
                            chunk.status = ChunkStatus.INDEXED
                        continue
                pending.append(chunk)

            for batch in self._iter_batches(pending):
                batch_created = await self._embed_and_persist_batch(
                    session=session,
                    embeddings_repo=embeddings_repo,
                    chunks_repo=chunks_repo,
                    version=version,
                    batch=batch,
                    force=force,
                )
                created += batch_created

            remaining = [
                chunk
                for chunk in pending
                if (
                    await embeddings_repo.find_active_match(
                        chunk_id=chunk.id,
                        embedding_model_id=self._embedding_model_id,
                        content_hash=chunk.content_hash,
                    )
                )
                is None
            ]
            failed = len(remaining)
            if failed:
                version.processing_status = ProcessingStatus.FAILED
                version.failure_reason = "partial_embedding_failure"
                await session.commit()
                raise PartialEmbeddingFailureError(
                    f"{failed} chunks failed embedding after retries"
                )

            await self._supersede_prior_versions(session, version)

            version.processing_status = ProcessingStatus.INDEXED
            version.indexed_at = datetime.now(UTC)
            version.failure_reason = None
            await session.commit()

            logger.info(
                "indexing_completed",
                extra={
                    "document_version_id": str(document_version_id),
                    "embeddings_created": created,
                    "embeddings_skipped": skipped,
                },
            )
            return IndexingResult(
                document_version_id=document_version_id,
                embedding_model_id=self._embedding_model_id,
                embeddings_created=created,
                embeddings_skipped=skipped,
                embeddings_failed=0,
                warnings=warnings,
            )

    async def _embed_and_persist_batch(
        self,
        *,
        session: AsyncSession,
        embeddings_repo: EmbeddingRepository,
        chunks_repo: ChunkRepository,
        version: DocumentVersion,
        batch: list[Chunk],
        force: bool,
    ) -> int:
        vectors = await self._embed_batch_with_split(batch)
        created = 0
        for chunk, vector in zip(batch, vectors, strict=True):
            if len(vector) != self._provider.dimensions:
                raise DimensionMismatchError(
                    f"Expected {self._provider.dimensions} dims, got {len(vector)}"
                )
            if force or (
                await embeddings_repo.find_active_match(
                    chunk_id=chunk.id,
                    embedding_model_id=self._embedding_model_id,
                    content_hash=chunk.content_hash,
                )
                is None
            ):
                await embeddings_repo.mark_stale_for_chunk_model(
                    chunk_id=chunk.id,
                    embedding_model_id=self._embedding_model_id,
                )
            generation = await embeddings_repo.next_generation(
                chunk_id=chunk.id,
                embedding_model_id=self._embedding_model_id,
            )
            try:
                await embeddings_repo.add(
                    Embedding(
                        organization_id=version.organization_id,
                        workspace_id=version.workspace_id,
                        knowledge_base_id=version.knowledge_base_id,
                        chunk_id=chunk.id,
                        document_version_id=version.id,
                        embedding_model_id=self._embedding_model_id,
                        model_key=self._provider.model_key,
                        vector=vector,
                        dimensions=self._provider.dimensions,
                        content_hash=chunk.content_hash,
                        generation=generation,
                        index_status=IndexStatus.INDEXED,
                    )
                )
            except Exception as exc:
                raise StorageWriteError(str(exc)) from exc
            chunk.status = ChunkStatus.INDEXED
            created += 1
        await session.flush()
        return created

    async def _embed_batch_with_split(self, batch: list[Chunk]) -> list[list[float]]:
        try:
            return await self._embed_texts([chunk.text for chunk in batch])
        except (ModelUnavailableError, EmbeddingTimeoutError, Exception):
            if len(batch) == 1:
                return await self._embed_single_with_retries(batch[0])
            if len(batch) > 1:
                mid = len(batch) // 2
                left = await self._embed_batch_with_split(batch[:mid])
                right = await self._embed_batch_with_split(batch[mid:])
                return left + right
            raise

    async def _embed_single_with_retries(self, chunk: Chunk) -> list[list[float]]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return await self._embed_texts([chunk.text])
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(0)
        if isinstance(last_error, IndexingError):
            raise last_error
        raise PartialEmbeddingFailureError(str(last_error)) from last_error

    async def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        started = time.perf_counter()
        try:
            vectors = await asyncio.wait_for(
                self._provider.embed_texts(texts),
                timeout=self._batch_timeout_seconds,
            )
        except TimeoutError as exc:
            raise EmbeddingTimeoutError("Embedding batch timed out") from exc
        except ModelUnavailableError:
            raise
        except Exception as exc:
            raise ModelUnavailableError(str(exc)) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "indexing_batch_completed",
            extra={"batch_size": len(texts), "latency_ms": latency_ms},
        )
        return vectors

    def _iter_batches(self, chunks: list[Chunk]) -> list[list[Chunk]]:
        batches: list[list[Chunk]] = []
        current: list[Chunk] = []
        current_chars = 0
        for chunk in chunks:
            next_chars = current_chars + len(chunk.text)
            if current and (len(current) >= self._batch_size or next_chars > self._max_batch_chars):
                batches.append(current)
                current = []
                current_chars = 0
            current.append(chunk)
            current_chars += len(chunk.text)
        if current:
            batches.append(current)
        return batches

    async def _supersede_prior_versions(
        self,
        session: AsyncSession,
        version: DocumentVersion,
    ) -> None:
        versions = DocumentVersionRepository(session)
        chunks_repo = ChunkRepository(session)
        embeddings_repo = EmbeddingRepository(session)
        siblings = await versions.list_for_document(
            TenantScope(
                organization_id=version.organization_id,
                workspace_id=version.workspace_id,
            ),
            version.knowledge_base_id,
            version.document_id,
        )
        prior_ids = [
            sibling.id
            for sibling in siblings
            if sibling.id != version.id
            and sibling.processing_status
            in {ProcessingStatus.INDEXED, ProcessingStatus.CHUNKED, ProcessingStatus.INDEXING}
        ]
        now = datetime.now(UTC)
        for sibling in siblings:
            if sibling.id in prior_ids:
                sibling.processing_status = ProcessingStatus.SUPERSEDED
                sibling.superseded_at = now
        await chunks_repo.mark_superseded_for_versions(prior_ids)
        await embeddings_repo.mark_stale_for_versions(prior_ids)
        await session.flush()

    async def _mark_failed(self, document_version_id: uuid.UUID, code: str) -> None:
        async with self._session_factory() as session:
            versions = DocumentVersionRepository(session)
            version = await versions.get(document_version_id)
            if version is None:
                return
            version.processing_status = ProcessingStatus.FAILED
            version.failure_reason = code
            await session.commit()
        logger.info(
            "indexing_failed",
            extra={"document_version_id": str(document_version_id), "failure_reason": code},
        )
