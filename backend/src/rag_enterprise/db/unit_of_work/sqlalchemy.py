"""SQLAlchemy Unit of Work implementation."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.db.unit_of_work.protocol import UnitOfWorkProtocol


class SQLAlchemyUnitOfWork(UnitOfWorkProtocol):
    """Async unit of work backed by a SQLAlchemy session."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._owns_session = False

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Unit of Work has not been started")
        return self._session

    async def __aenter__(self) -> SQLAlchemyUnitOfWork:
        if self._session is None:
            self._session = self._session_factory()
            self._owns_session = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._session is None or not self._owns_session:
            return

        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            await self._session.close()
            self._session = None
            self._owns_session = False

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    def bind_session(self, session: AsyncSession) -> SQLAlchemyUnitOfWork:
        """Reuse an existing session inside the current unit of work."""
        self._session = session
        self._owns_session = False
        return self
