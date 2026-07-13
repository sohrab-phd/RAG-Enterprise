"""Application container and FastAPI Depends providers.

This module establishes the DI pattern for future services (database sessions,
Redis clients, AI pipelines, etc.) without implementing business logic.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_enterprise.core.config.settings import Settings, get_settings
from rag_enterprise.db.session.factory import create_engine_and_session_factory


@dataclass
class AppContainer:
    """Lightweight service container for application-wide dependencies."""

    settings: Settings
    engine: AsyncEngine | None = None
    session_factory: async_sessionmaker[AsyncSession] | None = None
    # TODO: Add Redis client when caching layer is integrated
    # TODO: Add AI/embedding service providers when RAG layer is integrated
    _initialized: bool = field(default=False, repr=False)

    async def initialize(self) -> None:
        """Initialize external resources during application startup."""
        if self._initialized:
            return

        self.engine, self.session_factory = create_engine_and_session_factory(
            self.settings.database
        )
        # TODO: Wire Redis connection
        self._initialized = True

    async def shutdown(self) -> None:
        """Release external resources during application shutdown."""
        if not self._initialized:
            return

        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None

        # TODO: Close Redis connection
        self._initialized = False


_container: AppContainer | None = None


def get_container() -> AppContainer:
    """Return the application container singleton."""
    if _container is None:
        raise RuntimeError("Application container has not been initialized")
    return _container


def set_container(container: AppContainer) -> None:
    """Set the application container (called during lifespan startup)."""
    global _container
    _container = container


@asynccontextmanager
async def lifespan_container(settings: Settings) -> AsyncIterator[AppContainer]:
    """Create and manage the application container lifecycle."""
    container = AppContainer(settings=settings)
    await container.initialize()
    set_container(container)
    try:
        yield container
    finally:
        await container.shutdown()
        global _container
        _container = None


def get_settings_dep() -> Settings:
    """FastAPI dependency for settings injection."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
