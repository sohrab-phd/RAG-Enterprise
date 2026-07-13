"""Indexing service tests."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.indexing.exceptions import EmptyChunkListError, PartialEmbeddingFailureError
from rag_enterprise.indexing.models import Chunk
from rag_enterprise.indexing.providers import BgeM3EmbeddingProvider
from rag_enterprise.indexing.repositories import EmbeddingRepository
from rag_enterprise.indexing.service import IndexingService
from rag_enterprise.knowledge.enums import ProcessingStatus
from rag_enterprise.knowledge.repositories.document_version import DocumentVersionRepository
from tests.helpers.rag_seed import content_hash, seed_chunked_version


class FailingProvider(BgeM3EmbeddingProvider):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("provider down")


@pytest.mark.asyncio
async def test_index_document_version_success(
    rag_session_factory: async_sessionmaker[AsyncSession],
    indexing_service: IndexingService,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    async with rag_session_factory() as session:
        _, _, version, chunks = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=[
                "این یک متن فارسی برای آزمایش شاخص‌گذاری است.",
                "Second English paragraph for embedding coverage.",
            ],
            languages=["fa", "en"],
        )
        version_id = version.id
        chunk_ids = [chunk.id for chunk in chunks]

    result = await indexing_service.index_document_version(version_id)

    assert result.embeddings_created == 2
    assert result.embeddings_skipped == 0
    assert result.embeddings_failed == 0

    async with rag_session_factory() as session:
        version = await DocumentVersionRepository(session).get(version_id)
        assert version is not None
        assert version.processing_status == ProcessingStatus.INDEXED
        embeddings = await EmbeddingRepository(session).list()
        assert len(embeddings) == 2
        assert {row.chunk_id for row in embeddings} == set(chunk_ids)
        assert all(len(row.vector) == 1024 for row in embeddings)


@pytest.mark.asyncio
async def test_empty_chunk_list_fails(
    rag_session_factory: async_sessionmaker[AsyncSession],
    indexing_service: IndexingService,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    async with rag_session_factory() as session:
        _, _, version, _ = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=[],
        )
        version_id = version.id

    with pytest.raises(EmptyChunkListError):
        await indexing_service.index_document_version(version_id)

    async with rag_session_factory() as session:
        version = await DocumentVersionRepository(session).get(version_id)
        assert version is not None
        assert version.processing_status == ProcessingStatus.FAILED
        assert version.failure_reason == "empty_chunk_list"


@pytest.mark.asyncio
async def test_skip_unchanged_chunks_on_reindex(
    rag_session_factory: async_sessionmaker[AsyncSession],
    indexing_service: IndexingService,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    async with rag_session_factory() as session:
        _, _, version, _ = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=["Stable chunk body that should be skipped on second run."],
        )
        version_id = version.id

    first = await indexing_service.index_document_version(version_id)
    second = await indexing_service.index_document_version(version_id)

    assert first.embeddings_created == 1
    assert second.embeddings_created == 0
    assert second.embeddings_skipped == 1


@pytest.mark.asyncio
async def test_failed_batch_marks_version_failed(
    rag_session_factory: async_sessionmaker[AsyncSession],
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    service = IndexingService(
        session_factory=rag_session_factory,
        embedding_provider=FailingProvider(),
        retry_delays_seconds=(0.0, 0.0),
    )
    async with rag_session_factory() as session:
        _, _, version, _ = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=["will fail"],
        )
        version_id = version.id

    with pytest.raises((PartialEmbeddingFailureError, Exception)):
        await service.index_document_version(version_id)

    async with rag_session_factory() as session:
        version = await DocumentVersionRepository(session).get(version_id)
        assert version is not None
        assert version.processing_status == ProcessingStatus.FAILED


@pytest.mark.asyncio
async def test_reindex_bumps_generation_on_content_change(
    rag_session_factory: async_sessionmaker[AsyncSession],
    indexing_service: IndexingService,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    async with rag_session_factory() as session:
        _, _, version, chunks = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=["original content for hash"],
        )
        version_id = version.id
        chunk_id = chunks[0].id

    await indexing_service.index_document_version(version_id)

    async with rag_session_factory() as session:
        chunk = await session.get(Chunk, chunk_id)
        assert chunk is not None
        chunk.text = "changed content for hash"
        chunk.content_hash = content_hash(chunk.text)
        version = await DocumentVersionRepository(session).get(version_id)
        assert version is not None
        version.processing_status = ProcessingStatus.CHUNKED
        await session.commit()

    await indexing_service.index_document_version(version_id)

    async with rag_session_factory() as session:
        rows = list(await EmbeddingRepository(session).list())
        assert len(rows) == 2
        generations = sorted(row.generation for row in rows)
        assert generations == [1, 2]
        indexed = [row for row in rows if row.index_status == "indexed"]
        stale = [row for row in rows if row.index_status == "stale"]
        assert len(indexed) == 1
        assert len(stale) == 1


@pytest.mark.asyncio
async def test_resume_failed_indexing(
    rag_session_factory: async_sessionmaker[AsyncSession],
    indexing_service: IndexingService,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    async with rag_session_factory() as session:
        _, _, version, _ = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=["resume me please with enough characters"],
        )
        version.processing_status = ProcessingStatus.FAILED
        version.failure_reason = "partial_embedding_failure"
        await session.commit()
        version_id = version.id

    result = await indexing_service.resume_failed_indexing(version_id)
    assert result.embeddings_created == 1

    async with rag_session_factory() as session:
        version = await DocumentVersionRepository(session).get(version_id)
        assert version is not None
        assert version.processing_status == ProcessingStatus.INDEXED
