"""Embedding repository tests."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.indexing.enums import IndexStatus
from rag_enterprise.indexing.models import Embedding
from rag_enterprise.indexing.providers import BgeM3EmbeddingProvider
from rag_enterprise.indexing.repositories import EmbeddingRepository
from rag_enterprise.indexing.service import IndexingService
from tests.helpers.rag_seed import seed_chunked_version


@pytest.mark.asyncio
async def test_find_active_match_and_search(
    rag_session_factory: async_sessionmaker[AsyncSession],
    indexing_service: IndexingService,
    embedding_provider: BgeM3EmbeddingProvider,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    async with rag_session_factory() as session:
        kb, document, version, chunks = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=["repository search content unique phrase"],
        )
        version_id = version.id
        chunk = chunks[0]
        chunk_id = chunk.id
        content_hash = chunk.content_hash
        kb_id = kb.id
        document_id = document.id

    await indexing_service.index_document_version(version_id)

    async with rag_session_factory() as session:
        repo = EmbeddingRepository(session)
        match = await repo.find_active_match(
            chunk_id=chunk_id,
            embedding_model_id=indexing_service._embedding_model_id,
            content_hash=content_hash,
        )
        assert match is not None
        assert match.index_status == IndexStatus.INDEXED

        query = await embedding_provider.embed_query("repository search content")
        hits = await repo.search_cosine(
            organization_id=org_id,
            knowledge_base_id=kb_id,
            embedding_model_id=indexing_service._embedding_model_id,
            query_vector=query,
            top_k=3,
        )
        assert hits
        assert hits[0].document_id == document_id
        assert hits[0].chunk_id == chunk_id


@pytest.mark.asyncio
async def test_generation_and_stale(
    rag_session_factory: async_sessionmaker[AsyncSession],
    embedding_provider: BgeM3EmbeddingProvider,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    async with rag_session_factory() as session:
        kb, document, version, chunks = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=["gen"],
        )
        chunk = chunks[0]
        model_id = uuid.UUID("018f0000-0000-7000-8000-00000000b6e3")
        repo = EmbeddingRepository(session)
        vector = await embedding_provider.embed_texts([chunk.text])
        await repo.add(
            Embedding(
                organization_id=org_id,
                workspace_id=workspace_id,
                knowledge_base_id=kb.id,
                chunk_id=chunk.id,
                document_version_id=version.id,
                embedding_model_id=model_id,
                model_key=embedding_provider.model_key,
                vector=vector[0],
                dimensions=1024,
                content_hash=chunk.content_hash,
                generation=1,
                index_status=IndexStatus.INDEXED,
            )
        )
        await session.commit()
        next_gen = await repo.next_generation(chunk_id=chunk.id, embedding_model_id=model_id)
        assert next_gen == 2
        await repo.mark_stale_for_chunk_model(chunk_id=chunk.id, embedding_model_id=model_id)
        await session.commit()
        match = await repo.find_active_match(
            chunk_id=chunk.id,
            embedding_model_id=model_id,
            content_hash=chunk.content_hash,
        )
        assert match is None
