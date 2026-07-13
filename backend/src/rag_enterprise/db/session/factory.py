"""Async session factory."""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_enterprise.core.config.database import DatabaseSettings
from rag_enterprise.db.session.engine import create_async_engine_from_settings


def create_session_factory(
    engine: AsyncEngine,
    *,
    expire_on_commit: bool = False,
) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to an engine."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=expire_on_commit,
        autoflush=False,
        autocommit=False,
    )


def create_engine_and_session_factory(
    database: DatabaseSettings,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create an engine and session factory from settings."""
    engine = create_async_engine_from_settings(database)
    session_factory = create_session_factory(engine)
    return engine, session_factory
