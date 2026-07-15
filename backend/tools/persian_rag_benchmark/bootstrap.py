"""Bootstrap production AppContainer without starting HTTP."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from rag_enterprise.core.config.settings import Settings, get_settings
from rag_enterprise.core.dependencies.providers import AppContainer, lifespan_container


@asynccontextmanager
async def production_container(
    settings: Settings | None = None,
) -> AsyncIterator[AppContainer]:
    """Yield an initialized DI container wired exactly like FastAPI lifespan."""
    active = settings or get_settings()
    async with lifespan_container(active) as container:
        yield container
