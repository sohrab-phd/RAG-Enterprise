"""Persistence layer test fixtures."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_enterprise.core.config.database import DatabaseSettings
from rag_enterprise.db.base import ModelBase
from rag_enterprise.db.session.factory import create_engine_and_session_factory
from tests.db.support import SampleRecord, build_sample_record


@pytest.fixture
def test_database_settings() -> DatabaseSettings:
    return DatabaseSettings(url="sqlite+aiosqlite:///:memory:", echo=False)


@pytest.fixture
async def engine(test_database_settings: DatabaseSettings) -> AsyncEngine:
    engine, _ = create_engine_and_session_factory(test_database_settings)
    async with engine.begin() as connection:
        await connection.run_sync(ModelBase.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@pytest.fixture
async def session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncSession:
    async with session_factory() as session:
        yield session


@pytest.fixture
def sample_organization_id() -> uuid.UUID:
    return uuid.UUID("018f0000-0000-7000-8000-000000000001")


@pytest.fixture
def sample_workspace_id() -> uuid.UUID:
    return uuid.UUID("018f0000-0000-7000-8000-000000000002")


@pytest.fixture
def sample_record(
    sample_organization_id: uuid.UUID,
    sample_workspace_id: uuid.UUID,
) -> SampleRecord:
    return build_sample_record(
        organization_id=sample_organization_id,
        workspace_id=sample_workspace_id,
    )
