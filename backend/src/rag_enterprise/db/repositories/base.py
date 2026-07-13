"""SQLAlchemy repository base implementation."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_enterprise.db.base import ModelBase
from rag_enterprise.db.mixins.soft_delete import SoftDeleteMixin
from rag_enterprise.db.repositories.protocol import RepositoryProtocol


class SQLAlchemyRepository[T: ModelBase](RepositoryProtocol[T]):
    """Generic async repository for SQLAlchemy ORM models."""

    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self._session = session
        self._model = model

    async def get(self, entity_id: uuid.UUID) -> T | None:
        entity = await self._session.get(self._model, entity_id)
        if entity is None:
            return None
        if self._supports_soft_delete() and self._is_deleted(entity):
            return None
        return entity

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int | None = None,
        include_deleted: bool = False,
    ) -> Sequence[T]:
        statement = self._base_select(include_deleted=include_deleted).offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.scalars(statement)
        return result.all()

    async def add(self, entity: T) -> T:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def remove(self, entity: T) -> None:
        await self._session.delete(entity)
        await self._session.flush()

    async def exists(self, entity_id: uuid.UUID, *, include_deleted: bool = False) -> bool:
        statement = (
            select(func.count()).select_from(self._model).where(self._model.id == entity_id)  # type: ignore[attr-defined]
        )
        if self._supports_soft_delete() and not include_deleted:
            statement = statement.where(self._model.deleted_at.is_(None))  # type: ignore[attr-defined]
        result = await self._session.scalar(statement)
        return bool(result)

    def _base_select(self, *, include_deleted: bool) -> Select[tuple[T]]:
        statement = select(self._model)
        if self._supports_soft_delete() and not include_deleted:
            statement = statement.where(self._model.deleted_at.is_(None))  # type: ignore[attr-defined]
        return statement

    def _supports_soft_delete(self) -> bool:
        return issubclass(self._model, SoftDeleteMixin)

    @staticmethod
    def _is_deleted(entity: T) -> bool:
        if isinstance(entity, SoftDeleteMixin):
            return entity.is_deleted
        return False
