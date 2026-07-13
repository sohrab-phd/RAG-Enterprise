"""FastAPI database session dependency."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from rag_enterprise.core.dependencies.providers import get_container
from rag_enterprise.db.session.transaction import transaction


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped database session with automatic transaction handling."""
    container = get_container()
    if container.session_factory is None:
        raise RuntimeError("Database session factory has not been initialized")

    async with container.session_factory() as session, transaction(session):
        yield session
