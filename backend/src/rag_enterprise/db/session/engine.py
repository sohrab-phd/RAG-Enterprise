"""Async SQLAlchemy engine factory."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from rag_enterprise.core.config.database import DatabaseSettings


def create_async_engine_from_settings(database: DatabaseSettings) -> AsyncEngine:
    """Create an async engine from database settings."""
    url = database.resolved_url()

    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        if url.endswith("/:memory:"):
            return create_async_engine(
                url,
                echo=database.echo,
                connect_args=connect_args,
                poolclass=StaticPool,
            )
        return create_async_engine(url, echo=database.echo, connect_args=connect_args)

    return create_async_engine(
        url,
        echo=database.echo,
        pool_size=database.pool_size,
        max_overflow=database.max_overflow,
        pool_timeout=database.pool_timeout,
        pool_recycle=database.pool_recycle,
        pool_pre_ping=True,
    )
