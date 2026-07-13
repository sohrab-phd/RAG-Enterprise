"""Knowledge query handlers."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.application.common import Result
from rag_enterprise.application.dto.base import PaginationDTO
from rag_enterprise.knowledge import queries as qry
from rag_enterprise.knowledge.authorization import not_found, require_permission
from rag_enterprise.knowledge.dto import (
    DocumentDetailDTO,
    DocumentSummaryDTO,
    FolderContentsDTO,
    KnowledgeBaseDetailDTO,
    KnowledgeBaseSummaryDTO,
    TreeFolderNodeDTO,
    TreeViewDTO,
)
from rag_enterprise.knowledge.mappers import (
    to_document_detail,
    to_document_summary,
    to_folder_summary,
    to_kb_detail,
    to_kb_summary,
)
from rag_enterprise.knowledge.repositories.scope import TenantScope
from rag_enterprise.knowledge.unit_of_work import KnowledgeUnitOfWork


def _scope(query: qry._ScopedQuery) -> TenantScope:
    return TenantScope(query.actor.organization_id, query.workspace_id)


class GetKnowledgeBaseHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(self, query: qry.GetKnowledgeBaseQuery) -> Result[KnowledgeBaseDetailDTO]:
        auth = require_permission(query.actor, "knowledge_base:read")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(query)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            kb = await uow.knowledge_bases.get_scoped(scope, query.knowledge_base_id)
            if kb is None:
                return Result.fail(not_found("Knowledge base").error)  # type: ignore[arg-type]
            return Result.ok(to_kb_detail(kb))


class ListKnowledgeBasesHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(
        self,
        query: qry.ListKnowledgeBasesQuery,
    ) -> Result[PaginationDTO[KnowledgeBaseSummaryDTO]]:
        auth = require_permission(query.actor, "knowledge_base:read")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(query)
        offset = (query.page - 1) * query.page_size
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            total = await uow.knowledge_bases.count_scoped(
                scope,
                status=query.status,
                query=query.query,
                include_deleted=query.include_deleted,
            )
            items = await uow.knowledge_bases.list_scoped(
                scope,
                status=query.status,
                query=query.query,
                offset=offset,
                limit=query.page_size,
                include_deleted=query.include_deleted,
            )
            page: PaginationDTO[KnowledgeBaseSummaryDTO] = PaginationDTO(
                items=[to_kb_summary(item) for item in items],
                page=query.page,
                page_size=query.page_size,
                total_items=total,
            )
            return Result.ok(page)


class TreeViewHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(self, query: qry.TreeViewQuery) -> Result[TreeViewDTO]:
        auth = require_permission(query.actor, "folder:read")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(query)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            kb = await uow.knowledge_bases.get_scoped(scope, query.knowledge_base_id)
            if kb is None:
                return Result.fail(not_found("Knowledge base").error)  # type: ignore[arg-type]

            async def build_node(
                folder_id: uuid.UUID | None, depth: int
            ) -> list[TreeFolderNodeDTO]:
                if depth > query.depth:
                    return []
                children = await uow.folders.list_children(
                    scope,
                    query.knowledge_base_id,
                    parent_folder_id=folder_id,
                )
                nodes: list[TreeFolderNodeDTO] = []
                for folder in children:
                    doc_count = await uow.documents.count_in_folder(
                        scope,
                        query.knowledge_base_id,
                        folder_id=folder.id,
                    )
                    nodes.append(
                        TreeFolderNodeDTO(
                            id=folder.id,
                            name=folder.name,
                            status=folder.status,
                            document_count=doc_count,
                            children=await build_node(folder.id, depth + 1),
                        )
                    )
                return nodes

            return Result.ok(
                TreeViewDTO(
                    knowledge_base_id=query.knowledge_base_id,
                    folders=await build_node(None, 0),
                )
            )


class DocumentDetailsHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(self, query: qry.DocumentDetailsQuery) -> Result[DocumentDetailDTO]:
        auth = require_permission(query.actor, "document:read")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(query)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            document = await uow.documents.get_scoped(
                scope, query.knowledge_base_id, query.document_id
            )
            if document is None:
                return Result.fail(not_found("Document").error)  # type: ignore[arg-type]
            return Result.ok(to_document_detail(document))


class FolderContentsHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(self, query: qry.FolderContentsQuery) -> Result[FolderContentsDTO]:
        auth = require_permission(query.actor, "folder:read")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(query)
        offset = (query.page - 1) * query.page_size
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            if query.folder_id is not None:
                folder = await uow.folders.get_scoped(
                    scope, query.knowledge_base_id, query.folder_id
                )
                if folder is None:
                    return Result.fail(not_found("Folder").error)  # type: ignore[arg-type]
            folders = await uow.folders.list_children(
                scope,
                query.knowledge_base_id,
                parent_folder_id=query.folder_id,
            )
            total = await uow.documents.count_in_folder(
                scope,
                query.knowledge_base_id,
                folder_id=query.folder_id,
                status=query.status,
            )
            documents = await uow.documents.list_in_folder(
                scope,
                query.knowledge_base_id,
                folder_id=query.folder_id,
                status=query.status,
                offset=offset,
                limit=query.page_size,
            )
            pagination: PaginationDTO[DocumentSummaryDTO] = PaginationDTO(
                items=[to_document_summary(doc) for doc in documents],
                page=query.page,
                page_size=query.page_size,
                total_items=total,
            )
            return Result.ok(
                FolderContentsDTO(
                    folder_id=query.folder_id,
                    folders=[to_folder_summary(folder) for folder in folders],
                    documents=pagination.items,
                    pagination=pagination,
                )
            )


class SearchMetadataHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(
        self,
        query: qry.SearchMetadataQuery,
    ) -> Result[PaginationDTO[DocumentDetailDTO]]:
        auth = require_permission(query.actor, "document:read")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(query)
        offset = (query.page - 1) * query.page_size
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            kb = await uow.knowledge_bases.get_scoped(scope, query.knowledge_base_id)
            if kb is None:
                return Result.fail(not_found("Knowledge base").error)  # type: ignore[arg-type]
            documents = await uow.documents.search_metadata(
                scope,
                query.knowledge_base_id,
                query=query.query,
                offset=offset,
                limit=query.page_size,
            )
            page: PaginationDTO[DocumentDetailDTO] = PaginationDTO(
                items=[to_document_detail(doc) for doc in documents],
                page=query.page,
                page_size=query.page_size,
                total_items=len(documents),
            )
            return Result.ok(page)
