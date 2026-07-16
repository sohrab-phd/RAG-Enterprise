"""Register knowledge command and query handlers."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.application.commands.dispatcher import CommandDispatcher
from rag_enterprise.application.interfaces.file_storage import FileStorage
from rag_enterprise.application.queries.dispatcher import QueryDispatcher
from rag_enterprise.knowledge import commands as cmd
from rag_enterprise.knowledge import queries as qry
from rag_enterprise.knowledge.handlers import command_handlers as ch
from rag_enterprise.knowledge.handlers import query_handlers as qh


def register_knowledge_handlers(
    *,
    command_dispatcher: CommandDispatcher,
    query_dispatcher: QueryDispatcher,
    session_factory: async_sessionmaker[AsyncSession],
    file_storage: FileStorage,
) -> None:
    """Register all knowledge management handlers."""
    command_dispatcher.register(
        cmd.CreateKnowledgeBaseCommand,
        ch.CreateKnowledgeBaseHandler(session_factory),
    )
    command_dispatcher.register(
        cmd.UpdateKnowledgeBaseCommand,
        ch.UpdateKnowledgeBaseHandler(session_factory),
    )
    command_dispatcher.register(
        cmd.PublishKnowledgeBaseCommand,
        ch.PublishKnowledgeBaseHandler(session_factory),
    )
    command_dispatcher.register(
        cmd.ArchiveKnowledgeBaseCommand,
        ch.ArchiveKnowledgeBaseHandler(session_factory),
    )
    command_dispatcher.register(
        cmd.RestoreKnowledgeBaseCommand,
        ch.RestoreKnowledgeBaseHandler(session_factory),
    )
    command_dispatcher.register(
        cmd.DeleteKnowledgeBaseCommand,
        ch.DeleteKnowledgeBaseHandler(session_factory, file_storage),
    )
    command_dispatcher.register(cmd.CreateFolderCommand, ch.CreateFolderHandler(session_factory))
    command_dispatcher.register(cmd.MoveFolderCommand, ch.MoveFolderHandler(session_factory))
    command_dispatcher.register(
        cmd.CreateDocumentCommand,
        ch.CreateDocumentHandler(session_factory),
    )
    command_dispatcher.register(
        cmd.InitiateUploadCommand,
        ch.InitiateUploadHandler(session_factory, file_storage),
    )
    command_dispatcher.register(
        cmd.CompleteUploadCommand,
        ch.CompleteUploadHandler(session_factory, file_storage),
    )
    command_dispatcher.register(
        cmd.UploadDocumentVersionCommand,
        ch.UploadDocumentVersionHandler(session_factory, file_storage),
    )
    command_dispatcher.register(
        cmd.ArchiveDocumentCommand,
        ch.ArchiveDocumentHandler(session_factory),
    )
    command_dispatcher.register(
        cmd.RestoreDocumentCommand,
        ch.RestoreDocumentHandler(session_factory),
    )
    command_dispatcher.register(
        cmd.DeleteDocumentCommand,
        ch.DeleteDocumentHandler(session_factory, file_storage),
    )
    command_dispatcher.register(
        cmd.MoveDocumentCommand,
        ch.MoveDocumentHandler(session_factory),
    )
    command_dispatcher.register(
        cmd.UpdateDocumentMetadataCommand,
        ch.UpdateDocumentMetadataHandler(session_factory),
    )

    query_dispatcher.register(
        qry.GetKnowledgeBaseQuery,
        qh.GetKnowledgeBaseHandler(session_factory),
    )
    query_dispatcher.register(
        qry.ListKnowledgeBasesQuery,
        qh.ListKnowledgeBasesHandler(session_factory),
    )
    query_dispatcher.register(qry.TreeViewQuery, qh.TreeViewHandler(session_factory))
    query_dispatcher.register(
        qry.DocumentDetailsQuery,
        qh.DocumentDetailsHandler(session_factory),
    )
    query_dispatcher.register(
        qry.FolderContentsQuery,
        qh.FolderContentsHandler(session_factory),
    )
    query_dispatcher.register(
        qry.SearchMetadataQuery,
        qh.SearchMetadataHandler(session_factory),
    )
