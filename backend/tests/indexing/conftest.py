"""Shared fixtures for indexing and retrieval tests."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_enterprise.core.config.database import DatabaseSettings
from rag_enterprise.core.config.settings import get_settings
from rag_enterprise.core.dependencies.providers import AppContainer, set_container
from rag_enterprise.db.base import ModelBase
from rag_enterprise.db.session.factory import create_engine_and_session_factory
from rag_enterprise.indexing import models as indexing_models  # noqa: F401
from rag_enterprise.indexing.providers import BgeM3EmbeddingProvider
from rag_enterprise.indexing.service import IndexingService
from rag_enterprise.knowledge import models as knowledge_models  # noqa: F401
from rag_enterprise.knowledge.infrastructure.storage import InMemoryFileStorage
from rag_enterprise.knowledge.registration import register_knowledge_handlers
from rag_enterprise.retrieval.service import RetrievalService
from tests.helpers.rag_seed import ALL_PERMISSIONS, content_hash, seed_chunked_version

__all__ = ["ALL_PERMISSIONS", "content_hash", "seed_chunked_version"]


@pytest.fixture
def org_id() -> uuid.UUID:
    return uuid.UUID("018f0000-0000-7000-8000-000000000011")


@pytest.fixture
def workspace_id() -> uuid.UUID:
    return uuid.UUID("018f0000-0000-7000-8000-000000000012")


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.UUID("018f0000-0000-7000-8000-000000000013")


@pytest.fixture
def actor_headers(org_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, str]:
    return {
        "X-Organization-Id": str(org_id),
        "X-User-Id": str(user_id),
    }


@pytest.fixture
def embedding_provider() -> BgeM3EmbeddingProvider:
    return BgeM3EmbeddingProvider(mode="deterministic", dimensions=1024)


@pytest.fixture
async def rag_engine() -> AsyncEngine:
    settings = DatabaseSettings(url="sqlite+aiosqlite:///:memory:", echo=False)
    engine, _ = create_engine_and_session_factory(settings)
    async with engine.begin() as connection:
        await connection.run_sync(ModelBase.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def rag_session_factory(rag_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=rag_engine, expire_on_commit=False, autoflush=False)


@pytest.fixture
async def indexing_service(
    rag_session_factory: async_sessionmaker[AsyncSession],
    embedding_provider: BgeM3EmbeddingProvider,
) -> IndexingService:
    return IndexingService(
        session_factory=rag_session_factory,
        embedding_provider=embedding_provider,
        retry_delays_seconds=(0.0, 0.0, 0.0),
    )


@pytest.fixture
async def retrieval_service(
    rag_session_factory: async_sessionmaker[AsyncSession],
    embedding_provider: BgeM3EmbeddingProvider,
) -> RetrievalService:
    return RetrievalService(
        session_factory=rag_session_factory,
        embedding_provider=embedding_provider,
    )


@pytest.fixture
async def rag_container(
    rag_session_factory: async_sessionmaker[AsyncSession],
    rag_engine: AsyncEngine,
    embedding_provider: BgeM3EmbeddingProvider,
) -> AppContainer:
    container = AppContainer(settings=get_settings())
    container.engine = rag_engine
    container.session_factory = rag_session_factory
    container.file_storage = InMemoryFileStorage()
    container.embedding_provider = embedding_provider
    container.indexing_service = IndexingService(
        session_factory=rag_session_factory,
        embedding_provider=embedding_provider,
        retry_delays_seconds=(0.0, 0.0, 0.0),
    )
    container.retrieval_service = RetrievalService(
        session_factory=rag_session_factory,
        embedding_provider=embedding_provider,
    )
    register_knowledge_handlers(
        command_dispatcher=container.command_dispatcher,
        query_dispatcher=container.query_dispatcher,
        session_factory=rag_session_factory,
        file_storage=container.file_storage,
    )
    set_container(container)
    yield container
    import rag_enterprise.core.dependencies.providers as providers

    providers._container = None
