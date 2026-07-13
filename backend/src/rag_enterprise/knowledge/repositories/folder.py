"""Folder repository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from typing import cast

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_enterprise.db.repositories.base import SQLAlchemyRepository
from rag_enterprise.knowledge.enums import FolderStatus
from rag_enterprise.knowledge.models import Folder
from rag_enterprise.knowledge.repositories.scope import TenantScope


class FolderRepository(SQLAlchemyRepository[Folder]):
    """Persistence access for folders."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Folder)

    async def get_scoped(
        self,
        scope: TenantScope,
        knowledge_base_id: uuid.UUID,
        folder_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> Folder | None:
        statement = self._scoped_select(
            scope,
            knowledge_base_id,
            include_deleted=include_deleted,
        ).where(Folder.id == folder_id)
        return cast(Folder | None, await self._session.scalar(statement))

    async def list_children(
        self,
        scope: TenantScope,
        knowledge_base_id: uuid.UUID,
        *,
        parent_folder_id: uuid.UUID | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int | None = None,
        include_deleted: bool = False,
    ) -> Sequence[Folder]:
        statement = self._scoped_select(
            scope,
            knowledge_base_id,
            include_deleted=include_deleted,
        )
        if parent_folder_id is None:
            statement = statement.where(Folder.parent_folder_id.is_(None))
        else:
            statement = statement.where(Folder.parent_folder_id == parent_folder_id)
        if status is not None:
            statement = statement.where(Folder.status == status)
        statement = statement.order_by(Folder.name).offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.scalars(statement)
        return result.all()

    async def sibling_name_exists(
        self,
        knowledge_base_id: uuid.UUID,
        parent_folder_id: uuid.UUID | None,
        name: str,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        statement = (
            select(func.count())
            .select_from(Folder)
            .where(
                Folder.knowledge_base_id == knowledge_base_id,
                Folder.name == name.strip(),
                Folder.deleted_at.is_(None),
                Folder.status != FolderStatus.DELETED,
            )
        )
        if parent_folder_id is None:
            statement = statement.where(Folder.parent_folder_id.is_(None))
        else:
            statement = statement.where(Folder.parent_folder_id == parent_folder_id)
        if exclude_id is not None:
            statement = statement.where(Folder.id != exclude_id)
        result = await self._session.scalar(statement)
        return bool(result)

    async def list_subtree_ids(
        self,
        knowledge_base_id: uuid.UUID,
        root_folder_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        root = await self._session.get(Folder, root_folder_id)
        if root is None:
            return []
        prefix = root.path
        statement = select(Folder.id).where(
            Folder.knowledge_base_id == knowledge_base_id,
            Folder.path.like(f"{prefix}%"),
        )
        result = await self._session.scalars(statement)
        return list(result.all())

    async def archive_all_in_kb(self, knowledge_base_id: uuid.UUID) -> None:
        from datetime import UTC, datetime

        await self._session.execute(
            update(Folder)
            .where(
                Folder.knowledge_base_id == knowledge_base_id,
                Folder.deleted_at.is_(None),
                Folder.status == FolderStatus.ACTIVE,
            )
            .values(status=FolderStatus.ARCHIVED, archived_at=datetime.now(UTC))
        )

    def _scoped_select(
        self,
        scope: TenantScope,
        knowledge_base_id: uuid.UUID,
        *,
        include_deleted: bool,
    ) -> Select[tuple[Folder]]:
        statement = select(Folder).where(
            Folder.organization_id == scope.organization_id,
            Folder.workspace_id == scope.workspace_id,
            Folder.knowledge_base_id == knowledge_base_id,
        )
        if not include_deleted:
            statement = statement.where(Folder.deleted_at.is_(None))
        return statement
