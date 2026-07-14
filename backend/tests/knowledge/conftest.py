"""Knowledge management test fixtures."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_enterprise.core.config.database import DatabaseSettings
from rag_enterprise.core.config.settings import get_settings
from rag_enterprise.core.dependencies.providers import AppContainer, set_container
from rag_enterprise.db.base import ModelBase
from rag_enterprise.db.session.factory import create_engine_and_session_factory
from rag_enterprise.generation import persistence as generation_models  # noqa: F401
from rag_enterprise.indexing import models as indexing_models  # noqa: F401
from rag_enterprise.knowledge import models as knowledge_models  # noqa: F401


@pytest.fixture
def org_id() -> uuid.UUID:
    return uuid.UUID("018f0000-0000-7000-8000-000000000001")


@pytest.fixture
def workspace_id() -> uuid.UUID:
    return uuid.UUID("018f0000-0000-7000-8000-000000000002")


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.UUID("018f0000-0000-7000-8000-000000000003")


@pytest.fixture
def actor_headers(org_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, str]:
    return {
        "X-Organization-Id": str(org_id),
        "X-User-Id": str(user_id),
    }


@pytest.fixture
async def knowledge_engine() -> AsyncEngine:
    settings = DatabaseSettings(url="sqlite+aiosqlite:///:memory:", echo=False)
    engine, _ = create_engine_and_session_factory(settings)
    async with engine.begin() as connection:
        await connection.run_sync(ModelBase.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def knowledge_session_factory(
    knowledge_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=knowledge_engine, expire_on_commit=False, autoflush=False)


@pytest.fixture
async def knowledge_container(
    knowledge_session_factory: async_sessionmaker[AsyncSession],
    knowledge_engine: AsyncEngine,
) -> AppContainer:
    from rag_enterprise.knowledge.infrastructure.storage import InMemoryFileStorage
    from rag_enterprise.knowledge.registration import register_knowledge_handlers

    container = AppContainer(settings=get_settings())
    container.engine = knowledge_engine
    container.session_factory = knowledge_session_factory
    container.file_storage = InMemoryFileStorage()
    register_knowledge_handlers(
        command_dispatcher=container.command_dispatcher,
        query_dispatcher=container.query_dispatcher,
        session_factory=knowledge_session_factory,
        file_storage=container.file_storage,
    )
    set_container(container)
    yield container
    import rag_enterprise.core.dependencies.providers as providers

    providers._container = None
