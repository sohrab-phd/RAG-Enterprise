"""PostgreSQL + pgvector integration tests (skipped when DB unavailable)."""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from rag_enterprise.db.base import ModelBase
from rag_enterprise.indexing import models as indexing_models  # noqa: F401
from rag_enterprise.indexing.providers import BgeM3EmbeddingProvider
from rag_enterprise.indexing.service import IndexingService
from rag_enterprise.knowledge import models as knowledge_models  # noqa: F401
from rag_enterprise.retrieval.models import SearchRequest
from rag_enterprise.retrieval.service import RetrievalService
from tests.helpers.rag_seed import ALL_PERMISSIONS, seed_chunked_version

POSTGRES_URL = os.getenv(
    "DATABASE_TEST_URL",
    "postgresql+asyncpg://rag:rag_dev_password@localhost:5432/rag_enterprise_test",
)


async def _postgres_available(url: str) -> bool:
    try:
        engine = create_async_engine(url, pool_pre_ping=True)
        async with engine.connect() as connection:
            await connection.execute(__import__("sqlalchemy").text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS", "0") != "1",
    reason="Set RUN_POSTGRES_TESTS=1 with a running Postgres+pgvector instance",
)


@pytest.fixture
async def pg_engine() -> AsyncEngine:
    if not await _postgres_available(POSTGRES_URL):
        pytest.skip("PostgreSQL is not available")
    engine = create_async_engine(POSTGRES_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        await connection.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        await connection.run_sync(ModelBase.metadata.drop_all)
        await connection.run_sync(ModelBase.metadata.create_all)
    yield engine
    async with engine.begin() as connection:
        await connection.run_sync(ModelBase.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def pg_session_factory(pg_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=pg_engine, expire_on_commit=False, autoflush=False)


@pytest.mark.asyncio
async def test_postgres_index_and_retrieve(
    pg_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = BgeM3EmbeddingProvider(mode="deterministic")
    indexing = IndexingService(
        session_factory=pg_session_factory,
        embedding_provider=provider,
        retry_delays_seconds=(0.0,),
    )
    retrieval = RetrievalService(
        session_factory=pg_session_factory,
        embedding_provider=provider,
    )
    org_id = uuid.uuid4()
    workspace_id = uuid.uuid4()

    async with pg_session_factory() as session:
        kb, _, version, _ = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=["PostgreSQL pgvector integration chunk about leave policy"],
        )
        kb_id = kb.id
        version_id = version.id

    result = await indexing.index_document_version(version_id)
    assert result.embeddings_created == 1

    response = await retrieval.retrieve(
        SearchRequest(
            query_text="leave policy",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            top_k=3,
            permissions=ALL_PERMISSIONS,
        )
    )
    assert response.result_count >= 1
