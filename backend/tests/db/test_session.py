"""Session factory tests."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_enterprise.core.config.database import DatabaseSettings
from rag_enterprise.db.session.factory import create_engine_and_session_factory


@pytest.mark.asyncio
async def test_create_engine_and_session_factory_executes_query(
    test_database_settings: DatabaseSettings,
) -> None:
    engine, session_factory = create_engine_and_session_factory(test_database_settings)

    try:
        async with session_factory() as session:
            result = await session.scalar(text("SELECT 1"))
            assert result == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_session_factory_provides_async_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        assert isinstance(session, AsyncSession)


@pytest.mark.asyncio
async def test_engine_dispose_closes_pool(engine: AsyncEngine) -> None:
    await engine.dispose()
