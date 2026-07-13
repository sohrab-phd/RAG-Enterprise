"""Knowledge management unit of work."""

from __future__ import annotations

from functools import cached_property
from types import TracebackType

from rag_enterprise.db.unit_of_work.sqlalchemy import SQLAlchemyUnitOfWork
from rag_enterprise.knowledge.repositories import (
    DocumentRepository,
    DocumentVersionRepository,
    FolderRepository,
    KnowledgeBaseRepository,
    UploadSessionRepository,
)


class KnowledgeUnitOfWork(SQLAlchemyUnitOfWork):
    """Unit of work exposing knowledge repositories."""

    async def __aenter__(self) -> KnowledgeUnitOfWork:
        await super().__aenter__()
        return self

    @cached_property
    def knowledge_bases(self) -> KnowledgeBaseRepository:
        return KnowledgeBaseRepository(self.session)

    @cached_property
    def folders(self) -> FolderRepository:
        return FolderRepository(self.session)

    @cached_property
    def documents(self) -> DocumentRepository:
        return DocumentRepository(self.session)

    @cached_property
    def document_versions(self) -> DocumentVersionRepository:
        return DocumentVersionRepository(self.session)

    @cached_property
    def upload_sessions(self) -> UploadSessionRepository:
        return UploadSessionRepository(self.session)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        for attr in (
            "knowledge_bases",
            "folders",
            "documents",
            "document_versions",
            "upload_sessions",
        ):
            self.__dict__.pop(attr, None)
        await super().__aexit__(exc_type, exc, tb)
