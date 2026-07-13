"""Transaction helpers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def transaction(session: AsyncSession) -> AsyncIterator[AsyncSession]:
    """Commit on success and roll back on failure."""
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
