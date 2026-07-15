"""Retrieval service tests."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.indexing.service import IndexingService
from rag_enterprise.knowledge.enums import KnowledgeBaseStatus
from rag_enterprise.retrieval.exceptions import (
    InvalidQueryError,
    KnowledgeBaseUnavailableError,
    ModelMismatchError,
)
from rag_enterprise.retrieval.models import SearchRequest
from rag_enterprise.retrieval.service import RetrievalService
from tests.helpers.rag_seed import ALL_PERMISSIONS, seed_chunked_version


@pytest.mark.asyncio
async def test_retrieve_returns_ranked_chunks(
    rag_session_factory: async_sessionmaker[AsyncSession],
    indexing_service: IndexingService,
    retrieval_service: RetrievalService,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    async with rag_session_factory() as session:
        kb, document, version, _ = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=[
                "سیاست مرخصی کارکنان در سازمان شرح داده شده است.",
                "Completely unrelated gardening tips and soil moisture.",
            ],
            languages=["fa", "en"],
        )
        kb_id = kb.id
        document_id = document.id
        version_id = version.id

    await indexing_service.index_document_version(version_id)

    response = await retrieval_service.retrieve(
        SearchRequest(
            query_text="سیاست مرخصی کارکنان",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            top_k=5,
            permissions=ALL_PERMISSIONS,
        )
    )

    assert response.result_count >= 1
    assert response.results[0].knowledge_base_id == kb_id
    assert response.results[0].document_id == document_id
    assert 0.0 <= response.results[0].score <= 1.0
    scores = [item.score for item in response.results]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_document_filter(
    rag_session_factory: async_sessionmaker[AsyncSession],
    indexing_service: IndexingService,
    retrieval_service: RetrievalService,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    async with rag_session_factory() as session:
        kb, document, version, _ = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=["alpha content", "still alpha"],
        )
        kb_id = kb.id
        document_id = document.id
        version_id = version.id

    await indexing_service.index_document_version(version_id)

    response = await retrieval_service.retrieve(
        SearchRequest(
            query_text="alpha content",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            document_ids=[document_id],
            top_k=5,
            permissions=ALL_PERMISSIONS,
        )
    )
    assert all(item.document_id == document_id for item in response.results)


@pytest.mark.asyncio
async def test_language_filter(
    rag_session_factory: async_sessionmaker[AsyncSession],
    indexing_service: IndexingService,
    retrieval_service: RetrievalService,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    async with rag_session_factory() as session:
        kb, _, version, _ = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=["متن فارسی یک", "english only text"],
            languages=["fa", "en"],
        )
        kb_id = kb.id
        version_id = version.id

    await indexing_service.index_document_version(version_id)

    response = await retrieval_service.retrieve(
        SearchRequest(
            query_text="متن فارسی",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            language="fa",
            top_k=5,
            permissions=ALL_PERMISSIONS,
        )
    )
    assert response.result_count >= 1
    assert all(item.language == "fa" for item in response.results)


@pytest.mark.asyncio
async def test_retrieve_normalizes_arabic_yeh_kaf_before_embed(
    rag_session_factory: async_sessionmaker[AsyncSession],
    indexing_service: IndexingService,
    retrieval_service: RetrievalService,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    """Query text uses the same normalize_persian_text pipeline as documents."""
    async with rag_session_factory() as session:
        kb, _, version, _ = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=["سیاست مرخصی کارکنان در سازمان شرح داده شده است."],
            languages=["fa"],
        )
        kb_id = kb.id
        version_id = version.id

    await indexing_service.index_document_version(version_id)

    # Arabic yeh/kaf in the user question must not be embedded raw.
    response = await retrieval_service.retrieve(
        SearchRequest(
            query_text="سياست مرخصي كاركنان!!!",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            top_k=3,
            permissions=ALL_PERMISSIONS,
        )
    )
    assert response.query_text == "سیاست مرخصی کارکنان!"
    assert response.result_count >= 1


@pytest.mark.asyncio
async def test_empty_query_rejected(
    retrieval_service: RetrievalService,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    with pytest.raises(InvalidQueryError):
        await retrieval_service.retrieve(
            SearchRequest(
                query_text="   ",
                organization_id=org_id,
                workspace_id=workspace_id,
                knowledge_base_id=uuid.uuid4(),
                permissions=ALL_PERMISSIONS,
            )
        )


@pytest.mark.asyncio
async def test_no_indexed_content_warning(
    rag_session_factory: async_sessionmaker[AsyncSession],
    retrieval_service: RetrievalService,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    async with rag_session_factory() as session:
        kb, _, _, _ = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=["not indexed yet"],
        )
        kb_id = kb.id

    response = await retrieval_service.retrieve(
        SearchRequest(
            query_text="not indexed yet",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            permissions=ALL_PERMISSIONS,
        )
    )
    assert response.result_count == 0
    assert "no_indexed_content" in response.warnings


@pytest.mark.asyncio
async def test_model_mismatch(
    retrieval_service: RetrievalService,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    with pytest.raises(ModelMismatchError):
        await retrieval_service.retrieve(
            SearchRequest(
                query_text="hello",
                organization_id=org_id,
                workspace_id=workspace_id,
                knowledge_base_id=uuid.uuid4(),
                embedding_model_id=uuid.uuid4(),
                permissions=ALL_PERMISSIONS,
            )
        )


@pytest.mark.asyncio
async def test_archived_kb_unavailable(
    rag_session_factory: async_sessionmaker[AsyncSession],
    retrieval_service: RetrievalService,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    async with rag_session_factory() as session:
        kb, _, _, _ = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=["archived"],
            kb_status=KnowledgeBaseStatus.ARCHIVED,
        )
        kb_id = kb.id

    with pytest.raises(KnowledgeBaseUnavailableError):
        await retrieval_service.retrieve(
            SearchRequest(
                query_text="archived",
                organization_id=org_id,
                workspace_id=workspace_id,
                knowledge_base_id=kb_id,
                permissions=ALL_PERMISSIONS,
            )
        )
