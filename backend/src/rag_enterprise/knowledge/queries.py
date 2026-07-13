"""Knowledge management queries."""

from __future__ import annotations

import uuid

from rag_enterprise.application.queries.base import QueryBase
from rag_enterprise.knowledge.context import RequestActor


class _ScopedQuery(QueryBase):
    actor: RequestActor
    workspace_id: uuid.UUID


class GetKnowledgeBaseQuery(_ScopedQuery):
    knowledge_base_id: uuid.UUID


class ListKnowledgeBasesQuery(_ScopedQuery):
    status: str | None = None
    query: str | None = None
    page: int = 1
    page_size: int = 20
    include_deleted: bool = False


class TreeViewQuery(_ScopedQuery):
    knowledge_base_id: uuid.UUID
    depth: int = 3


class DocumentDetailsQuery(_ScopedQuery):
    knowledge_base_id: uuid.UUID
    document_id: uuid.UUID


class FolderContentsQuery(_ScopedQuery):
    knowledge_base_id: uuid.UUID
    folder_id: uuid.UUID | None = None
    page: int = 1
    page_size: int = 20
    status: str | None = None


class SearchMetadataQuery(_ScopedQuery):
    knowledge_base_id: uuid.UUID
    query: str
    page: int = 1
    page_size: int = 20
