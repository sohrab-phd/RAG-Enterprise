"""Shared pytest fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient

from rag_enterprise.main import create_app


@pytest.fixture
def app():
    """Create a fresh FastAPI application instance for each test."""
    return create_app()


@pytest.fixture
async def client(app):
    """Async HTTP client bound to the test application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
