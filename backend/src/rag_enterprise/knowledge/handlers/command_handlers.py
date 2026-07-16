"""Knowledge command handlers."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.application.common import Result
from rag_enterprise.application.interfaces.file_storage import FileStorage
from rag_enterprise.generation.repositories import ConversationRepository, MessageRepository
from rag_enterprise.indexing.repositories import ChunkRepository, EmbeddingRepository
from rag_enterprise.knowledge import commands as cmd
from rag_enterprise.knowledge.authorization import conflict, not_found, require_permission
from rag_enterprise.knowledge.constants import MAX_FOLDER_DEPTH, UPLOAD_SESSION_TTL_HOURS
from rag_enterprise.knowledge.dto import KnowledgeBaseDetailDTO, UploadSessionDTO
from rag_enterprise.knowledge.enums import (
    DocumentStatus,
    FolderStatus,
    KnowledgeBaseStatus,
    UploadSessionStatus,
)
from rag_enterprise.knowledge.infrastructure.storage import (
    staging_storage_key,
    storage_key_for_version,
)
from rag_enterprise.knowledge.mappers import to_kb_detail, to_upload_session
from rag_enterprise.knowledge.models import (
    Document,
    DocumentVersion,
    Folder,
    KnowledgeBase,
    UploadSession,
)
from rag_enterprise.knowledge.repositories.scope import TenantScope
from rag_enterprise.knowledge.unit_of_work import KnowledgeUnitOfWork


def _scope(command: cmd._ScopedCommand) -> TenantScope:
    return TenantScope(
        organization_id=command.actor.organization_id,
        workspace_id=command.workspace_id,
    )


def _folder_path(parent: Folder | None, name: str) -> str:
    if parent is None:
        return f"/{name.strip()}"
    return f"{parent.path}/{name.strip()}"


class CreateKnowledgeBaseHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(
        self, command: cmd.CreateKnowledgeBaseCommand
    ) -> Result[KnowledgeBaseDetailDTO]:
        auth = require_permission(command.actor, "workspace:knowledge_base:create")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = TenantScope(command.actor.organization_id, command.workspace_id)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            if await uow.knowledge_bases.name_exists(scope, command.name):
                return Result.fail(conflict("Knowledge base name already exists").error)  # type: ignore[arg-type]
            entity = KnowledgeBase(
                organization_id=scope.organization_id,
                workspace_id=scope.workspace_id,
                name=command.name.strip(),
                description=command.description,
                status=KnowledgeBaseStatus.DRAFT,
                default_language=command.default_language,
                visibility_policy=command.visibility_policy,
                created_by_user_id=command.actor.user_id,
                updated_by_user_id=command.actor.user_id,
            )
            await uow.knowledge_bases.add(entity)
            await uow.commit()
            return Result.ok(to_kb_detail(entity))


class UpdateKnowledgeBaseHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(
        self, command: cmd.UpdateKnowledgeBaseCommand
    ) -> Result[KnowledgeBaseDetailDTO]:
        auth = require_permission(command.actor, "knowledge_base:manage")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(command)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            kb = await uow.knowledge_bases.get_scoped(scope, command.knowledge_base_id)
            if kb is None:
                return Result.fail(not_found("Knowledge base").error)  # type: ignore[arg-type]
            if kb.status in {KnowledgeBaseStatus.ARCHIVED, KnowledgeBaseStatus.DELETED}:
                return Result.fail(conflict("Knowledge base is not mutable").error)  # type: ignore[arg-type]
            if command.expected_version is not None and kb.row_version != command.expected_version:
                return Result.fail(conflict("Version conflict").error)  # type: ignore[arg-type]
            if command.name is not None:
                if await uow.knowledge_bases.name_exists(scope, command.name, exclude_id=kb.id):
                    return Result.fail(conflict("Knowledge base name already exists").error)  # type: ignore[arg-type]
                kb.name = command.name.strip()
            if command.default_language is not None:
                kb.default_language = command.default_language
            if command.visibility_policy is not None:
                kb.visibility_policy = command.visibility_policy
            if command.description is not None:
                kb.description = command.description
            kb.updated_by_user_id = command.actor.user_id
            kb.row_version += 1
            await uow.commit()
            return Result.ok(to_kb_detail(kb))


class PublishKnowledgeBaseHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(
        self, command: cmd.PublishKnowledgeBaseCommand
    ) -> Result[KnowledgeBaseDetailDTO]:
        auth = require_permission(command.actor, "knowledge_base:manage")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(command)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            kb = await uow.knowledge_bases.get_scoped(scope, command.knowledge_base_id)
            if kb is None:
                return Result.fail(not_found("Knowledge base").error)  # type: ignore[arg-type]
            if kb.status == KnowledgeBaseStatus.ACTIVE:
                return Result.ok(to_kb_detail(kb))
            if kb.status != KnowledgeBaseStatus.DRAFT:
                return Result.fail(conflict("Knowledge base is not draft").error)  # type: ignore[arg-type]
            await uow.knowledge_bases.publish(
                kb,
                updated_by_user_id=command.actor.user_id,
            )
            await uow.commit()
            return Result.ok(to_kb_detail(kb))


class ArchiveKnowledgeBaseHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(
        self, command: cmd.ArchiveKnowledgeBaseCommand
    ) -> Result[KnowledgeBaseDetailDTO]:
        auth = require_permission(command.actor, "knowledge_base:manage")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(command)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            kb = await uow.knowledge_bases.get_scoped(scope, command.knowledge_base_id)
            if kb is None:
                return Result.fail(not_found("Knowledge base").error)  # type: ignore[arg-type]
            if kb.status == KnowledgeBaseStatus.ARCHIVED:
                return Result.ok(to_kb_detail(kb))
            if kb.status == KnowledgeBaseStatus.DELETED:
                return Result.fail(conflict("Knowledge base is deleted").error)  # type: ignore[arg-type]
            now = datetime.now(UTC)
            kb.status = KnowledgeBaseStatus.ARCHIVED
            kb.archived_at = now
            kb.updated_by_user_id = command.actor.user_id
            kb.row_version += 1
            await uow.folders.archive_all_in_kb(kb.id)
            await uow.documents.archive_all_in_kb(kb.id)
            await uow.commit()
            return Result.ok(to_kb_detail(kb))


class RestoreKnowledgeBaseHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(
        self, command: cmd.RestoreKnowledgeBaseCommand
    ) -> Result[KnowledgeBaseDetailDTO]:
        auth = require_permission(command.actor, "knowledge_base:manage")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(command)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            kb = await uow.knowledge_bases.get_scoped(scope, command.knowledge_base_id)
            if kb is None:
                return Result.fail(not_found("Knowledge base").error)  # type: ignore[arg-type]
            if kb.status != KnowledgeBaseStatus.ARCHIVED:
                return Result.fail(conflict("Knowledge base is not archived").error)  # type: ignore[arg-type]
            kb.status = KnowledgeBaseStatus.ACTIVE
            kb.archived_at = None
            kb.updated_by_user_id = command.actor.user_id
            kb.row_version += 1
            await uow.commit()
            return Result.ok(to_kb_detail(kb))


class DeleteKnowledgeBaseHandler:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        file_storage: FileStorage,
    ) -> None:
        self._session_factory = session_factory
        self._file_storage = file_storage

    async def handle(self, command: cmd.DeleteKnowledgeBaseCommand) -> Result[None]:
        auth = require_permission(command.actor, "knowledge_base:manage")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(command)
        storage_keys: list[str] = []
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            kb = await uow.knowledge_bases.get_scoped(scope, command.knowledge_base_id)
            if kb is None:
                return Result.fail(not_found("Knowledge base").error)  # type: ignore[arg-type]
            if await uow.documents.has_legal_hold_in_kb(kb.id):
                return Result.fail(
                    conflict("Knowledge base has documents under legal hold").error
                )  # type: ignore[arg-type]

            storage_keys.extend(await uow.document_versions.list_storage_keys_for_kb(kb.id))
            storage_keys.extend(await uow.upload_sessions.list_staging_keys_for_kb(kb.id))

            messages = MessageRepository(uow.session)
            conversations = ConversationRepository(uow.session)
            embeddings = EmbeddingRepository(uow.session)
            chunks = ChunkRepository(uow.session)

            await messages.delete_all_for_knowledge_base(kb.id)
            await conversations.delete_all_for_knowledge_base(kb.id)
            await embeddings.delete_all_for_knowledge_base(kb.id)
            await chunks.delete_all_for_knowledge_base(kb.id)
            await uow.document_versions.delete_all_for_knowledge_base(kb.id)
            await uow.upload_sessions.delete_all_for_knowledge_base(kb.id)
            await uow.documents.hard_delete_all_in_kb(kb.id)
            await uow.folders.hard_delete_all_in_kb(kb.id)
            await uow.knowledge_bases.remove(kb)
            await uow.commit()

        await self._best_effort_delete_files(storage_keys)
        return Result.ok(None)

    async def _best_effort_delete_files(self, keys: list[str]) -> None:
        seen: set[str] = set()
        for key in keys:
            if not key or key in seen:
                continue
            seen.add(key)
            try:
                await self._file_storage.delete(key=key)
            except Exception:  # noqa: BLE001 — missing/corrupt files must not fail deletion
                continue


class CreateFolderHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(self, command: cmd.CreateFolderCommand) -> Result[Folder]:
        auth = require_permission(command.actor, "folder:manage")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(command)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            kb = await uow.knowledge_bases.get_scoped(scope, command.knowledge_base_id)
            if kb is None or kb.status == KnowledgeBaseStatus.ARCHIVED:
                return Result.fail(conflict("Knowledge base is not available").error)  # type: ignore[arg-type]
            parent: Folder | None = None
            if command.parent_folder_id is not None:
                parent = await uow.folders.get_scoped(
                    scope, command.knowledge_base_id, command.parent_folder_id
                )
                if parent is None or parent.status != FolderStatus.ACTIVE:
                    return Result.fail(not_found("Parent folder").error)  # type: ignore[arg-type]
            depth = 0 if parent is None else parent.depth + 1
            if depth >= MAX_FOLDER_DEPTH:
                return Result.fail(conflict("Maximum folder depth exceeded").error)  # type: ignore[arg-type]
            if await uow.folders.sibling_name_exists(
                command.knowledge_base_id, command.parent_folder_id, command.name
            ):
                return Result.fail(conflict("Folder name already exists").error)  # type: ignore[arg-type]
            folder = Folder(
                organization_id=scope.organization_id,
                workspace_id=scope.workspace_id,
                knowledge_base_id=command.knowledge_base_id,
                parent_folder_id=command.parent_folder_id,
                name=command.name.strip(),
                path=_folder_path(parent, command.name),
                depth=depth,
                created_by_user_id=command.actor.user_id,
                updated_by_user_id=command.actor.user_id,
            )
            await uow.folders.add(folder)
            await uow.commit()
            return Result.ok(folder)


class MoveFolderHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(self, command: cmd.MoveFolderCommand) -> Result[Folder]:
        auth = require_permission(command.actor, "folder:manage")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(command)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            folder = await uow.folders.get_scoped(
                scope, command.knowledge_base_id, command.folder_id
            )
            if folder is None or folder.status != FolderStatus.ACTIVE:
                return Result.fail(not_found("Folder").error)  # type: ignore[arg-type]
            if (
                command.expected_version is not None
                and folder.row_version != command.expected_version
            ):
                return Result.fail(conflict("Version conflict").error)  # type: ignore[arg-type]
            target_parent: Folder | None = None
            if command.target_parent_folder_id is not None:
                if command.target_parent_folder_id == folder.id:
                    return Result.fail(conflict("Cannot move folder into itself").error)  # type: ignore[arg-type]
                target_parent = await uow.folders.get_scoped(
                    scope, command.knowledge_base_id, command.target_parent_folder_id
                )
                if target_parent is None or target_parent.status != FolderStatus.ACTIVE:
                    return Result.fail(not_found("Target folder").error)  # type: ignore[arg-type]
                if target_parent.path.startswith(f"{folder.path}/"):
                    return Result.fail(conflict("Cannot move folder into its descendant").error)  # type: ignore[arg-type]
            new_depth = 0 if target_parent is None else target_parent.depth + 1
            subtree_ids = await uow.folders.list_subtree_ids(command.knowledge_base_id, folder.id)
            max_extra = 0
            for fid in subtree_ids:
                child = await uow.folders.get_scoped(scope, command.knowledge_base_id, fid)
                if child is None:
                    continue
                max_extra = max(max_extra, child.depth - folder.depth)
            if new_depth + max_extra >= MAX_FOLDER_DEPTH:
                return Result.fail(conflict("Maximum folder depth exceeded").error)  # type: ignore[arg-type]
            if await uow.folders.sibling_name_exists(
                command.knowledge_base_id,
                command.target_parent_folder_id,
                folder.name,
                exclude_id=folder.id,
            ):
                return Result.fail(conflict("Folder name already exists at target").error)  # type: ignore[arg-type]
            old_path = folder.path
            folder.parent_folder_id = command.target_parent_folder_id
            folder.path = _folder_path(target_parent, folder.name)
            folder.depth = new_depth
            folder.row_version += 1
            folder.updated_by_user_id = command.actor.user_id
            for child_id in subtree_ids:
                if child_id == folder.id:
                    continue
                child = await uow.folders.get_scoped(scope, command.knowledge_base_id, child_id)
                if child is None:
                    continue
                child.path = child.path.replace(old_path, folder.path, 1)
                child.depth = len([part for part in child.path.split("/") if part]) - 1
                child.row_version += 1
            await uow.commit()
            return Result.ok(folder)


class CreateDocumentHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(self, command: cmd.CreateDocumentCommand) -> Result[Document]:
        auth = require_permission(command.actor, "document:create")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(command)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            kb = await uow.knowledge_bases.get_scoped(scope, command.knowledge_base_id)
            if kb is None or kb.status == KnowledgeBaseStatus.ARCHIVED:
                return Result.fail(conflict("Knowledge base is not available").error)  # type: ignore[arg-type]
            if command.folder_id is not None:
                folder = await uow.folders.get_scoped(
                    scope, command.knowledge_base_id, command.folder_id
                )
                if folder is None or folder.status != FolderStatus.ACTIVE:
                    return Result.fail(not_found("Folder").error)  # type: ignore[arg-type]
            language = command.declared_language or kb.default_language
            document = Document(
                organization_id=scope.organization_id,
                workspace_id=scope.workspace_id,
                knowledge_base_id=command.knowledge_base_id,
                folder_id=command.folder_id,
                title=command.title.strip(),
                declared_language=language,
                source_type=command.source_type,
                classification_label=command.classification_label,
                tags=command.tags,
                metadata_json=command.metadata,
                owner_user_id=command.actor.user_id,
                created_by_user_id=command.actor.user_id,
                updated_by_user_id=command.actor.user_id,
            )
            await uow.documents.add(document)
            kb.document_count += 1
            await uow.commit()
            return Result.ok(document)


class InitiateUploadHandler:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        file_storage: FileStorage,
    ) -> None:
        self._session_factory = session_factory
        self._file_storage = file_storage

    async def handle(self, command: cmd.InitiateUploadCommand) -> Result[UploadSessionDTO]:
        del self._file_storage
        auth = require_permission(command.actor, "document:create")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(command)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            kb = await uow.knowledge_bases.get_scoped(scope, command.knowledge_base_id)
            if kb is None or kb.status == KnowledgeBaseStatus.ARCHIVED:
                return Result.fail(conflict("Knowledge base is not available").error)  # type: ignore[arg-type]
            session = UploadSession(
                organization_id=scope.organization_id,
                workspace_id=scope.workspace_id,
                knowledge_base_id=command.knowledge_base_id,
                document_id=command.document_id,
                file_name=command.file_name,
                file_size_bytes=command.file_size_bytes,
                mime_type=command.mime_type,
                checksum_sha256=command.checksum_sha256,
                expires_at=datetime.now(UTC) + timedelta(hours=UPLOAD_SESSION_TTL_HOURS),
                created_by_user_id=command.actor.user_id,
            )
            await uow.upload_sessions.add(session)
            session.storage_key_staging = staging_storage_key(
                session.id,
                organization_id=scope.organization_id,
                workspace_id=scope.workspace_id,
            )
            await uow.session.flush()
            await uow.commit()
            return Result.ok(to_upload_session(session))


class CompleteUploadHandler:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        file_storage: FileStorage,
    ) -> None:
        self._session_factory = session_factory
        self._file_storage = file_storage

    async def handle(self, command: cmd.CompleteUploadCommand) -> Result[UploadSessionDTO]:
        auth = require_permission(command.actor, "document:create")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(command)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            session = await uow.upload_sessions.get_scoped(
                scope, command.knowledge_base_id, command.upload_id
            )
            if session is None:
                return Result.fail(not_found("Upload session").error)  # type: ignore[arg-type]
            if session.status == UploadSessionStatus.COMPLETED:
                return Result.ok(to_upload_session(session))
            if session.status != UploadSessionStatus.PENDING:
                return Result.fail(conflict("Upload session is not completable").error)  # type: ignore[arg-type]
            if session.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
                session.status = UploadSessionStatus.EXPIRED
                await uow.commit()
                return Result.fail(conflict("Upload session expired").error)  # type: ignore[arg-type]
            if command.content is None:
                return Result.fail(conflict("Upload content is required").error)  # type: ignore[arg-type]
            if len(command.content) != session.file_size_bytes:
                return Result.fail(conflict("Upload size mismatch").error)  # type: ignore[arg-type]
            digest = hashlib.sha256(command.content).hexdigest()
            if command.checksum_sha256 and command.checksum_sha256 != digest:
                return Result.fail(conflict("Checksum mismatch").error)  # type: ignore[arg-type]
            key = session.storage_key_staging or staging_storage_key(
                session.id,
                organization_id=scope.organization_id,
                workspace_id=scope.workspace_id,
            )
            await self._file_storage.put(
                organization_id=scope.organization_id,
                workspace_id=scope.workspace_id,
                key=key,
                data=command.content,
                content_type=session.mime_type,
            )
            session.checksum_sha256 = digest
            session.status = UploadSessionStatus.COMPLETED
            session.completed_at = datetime.now(UTC)
            await uow.commit()
            return Result.ok(to_upload_session(session))


class UploadDocumentVersionHandler:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        file_storage: FileStorage,
    ) -> None:
        self._session_factory = session_factory
        self._file_storage = file_storage

    async def handle(self, command: cmd.UploadDocumentVersionCommand) -> Result[DocumentVersion]:
        auth = require_permission(command.actor, "document:update")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(command)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            document = await uow.documents.get_scoped(
                scope, command.knowledge_base_id, command.document_id
            )
            if document is None:
                return Result.fail(not_found("Document").error)  # type: ignore[arg-type]
            if document.status in {DocumentStatus.ARCHIVED, DocumentStatus.DELETED}:
                return Result.fail(conflict("Document is not mutable").error)  # type: ignore[arg-type]
            session = await uow.upload_sessions.get_scoped(
                scope, command.knowledge_base_id, command.upload_id
            )
            if session is None or session.status != UploadSessionStatus.COMPLETED:
                return Result.fail(conflict("Upload is not completed").error)  # type: ignore[arg-type]
            if await uow.document_versions.get_by_upload_session(session.id):
                return Result.fail(conflict("Upload already bound to a version").error)  # type: ignore[arg-type]
            staging_key = session.storage_key_staging
            if staging_key is None or session.checksum_sha256 is None:
                return Result.fail(conflict("Upload is missing staged content").error)  # type: ignore[arg-type]
            content = await self._file_storage.get(key=staging_key)
            version_number = await uow.document_versions.next_version_number(document.id)
            version_id = uuid.uuid4()
            permanent_key = storage_key_for_version(
                organization_id=scope.organization_id,
                workspace_id=scope.workspace_id,
                knowledge_base_id=command.knowledge_base_id,
                document_id=document.id,
                version_id=version_id,
                file_name=session.file_name,
            )
            version = DocumentVersion(
                id=version_id,
                organization_id=scope.organization_id,
                workspace_id=scope.workspace_id,
                knowledge_base_id=command.knowledge_base_id,
                document_id=document.id,
                version_number=version_number,
                content_hash=session.checksum_sha256,
                file_name=session.file_name,
                file_size_bytes=session.file_size_bytes,
                mime_type=session.mime_type or "application/octet-stream",
                storage_key_original=permanent_key,
                change_summary=command.change_summary,
                upload_session_id=session.id,
                created_by_user_id=command.actor.user_id,
            )
            await self._file_storage.put(
                organization_id=scope.organization_id,
                workspace_id=scope.workspace_id,
                key=version.storage_key_original,
                data=content,
                content_type=version.mime_type,
            )
            await uow.document_versions.add(version)
            document.current_version_id = version.id
            document.updated_by_user_id = command.actor.user_id
            document.row_version += 1
            if document.status == DocumentStatus.DRAFT:
                document.status = DocumentStatus.ACTIVE
            await uow.commit()
            return Result.ok(version)


class ArchiveDocumentHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(self, command: cmd.ArchiveDocumentCommand) -> Result[Document]:
        auth = require_permission(command.actor, "document:update")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(command)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            document = await uow.documents.get_scoped(
                scope, command.knowledge_base_id, command.document_id
            )
            if document is None:
                return Result.fail(not_found("Document").error)  # type: ignore[arg-type]
            if document.status == DocumentStatus.ARCHIVED:
                return Result.ok(document)
            document.status = DocumentStatus.ARCHIVED
            document.archived_at = datetime.now(UTC)
            document.updated_by_user_id = command.actor.user_id
            document.row_version += 1
            await uow.commit()
            return Result.ok(document)


class RestoreDocumentHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(self, command: cmd.RestoreDocumentCommand) -> Result[Document]:
        auth = require_permission(command.actor, "document:update")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(command)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            document = await uow.documents.get_scoped(
                scope, command.knowledge_base_id, command.document_id
            )
            if document is None:
                return Result.fail(not_found("Document").error)  # type: ignore[arg-type]
            if document.status != DocumentStatus.ARCHIVED:
                return Result.fail(conflict("Document is not archived").error)  # type: ignore[arg-type]
            if document.folder_id is not None:
                folder = await uow.folders.get_scoped(
                    scope, command.knowledge_base_id, document.folder_id
                )
                if folder is None or folder.status != FolderStatus.ACTIVE:
                    return Result.fail(conflict("Restore parent folder first").error)  # type: ignore[arg-type]
            document.status = DocumentStatus.ACTIVE
            document.archived_at = None
            document.updated_by_user_id = command.actor.user_id
            document.row_version += 1
            await uow.commit()
            return Result.ok(document)


class DeleteDocumentHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(self, command: cmd.DeleteDocumentCommand) -> Result[None]:
        auth = require_permission(command.actor, "document:delete")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(command)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            document = await uow.documents.get_scoped(
                scope, command.knowledge_base_id, command.document_id
            )
            if document is None:
                return Result.fail(not_found("Document").error)  # type: ignore[arg-type]
            if document.legal_hold:
                return Result.fail(conflict("Document is under legal hold").error)  # type: ignore[arg-type]
            if document.status == DocumentStatus.DELETED:
                return Result.ok(None)
            now = datetime.now(UTC)
            document.status = DocumentStatus.DELETED
            document.deleted_at = now
            document.deleted_by_user_id = command.actor.user_id
            document.row_version += 1
            kb = await uow.knowledge_bases.get_scoped(scope, command.knowledge_base_id)
            if kb is not None and kb.document_count > 0:
                kb.document_count -= 1
            await uow.commit()
            return Result.ok(None)


class MoveDocumentHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(self, command: cmd.MoveDocumentCommand) -> Result[Document]:
        auth = require_permission(command.actor, "document:update")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(command)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            document = await uow.documents.get_scoped(
                scope, command.knowledge_base_id, command.document_id
            )
            if document is None or document.status not in {
                DocumentStatus.DRAFT,
                DocumentStatus.ACTIVE,
            }:
                return Result.fail(conflict("Document is not movable").error)  # type: ignore[arg-type]
            if command.target_folder_id is not None:
                folder = await uow.folders.get_scoped(
                    scope, command.knowledge_base_id, command.target_folder_id
                )
                if folder is None or folder.status != FolderStatus.ACTIVE:
                    return Result.fail(not_found("Target folder").error)  # type: ignore[arg-type]
            document.folder_id = command.target_folder_id
            document.updated_by_user_id = command.actor.user_id
            document.row_version += 1
            await uow.commit()
            return Result.ok(document)


class UpdateDocumentMetadataHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(self, command: cmd.UpdateDocumentMetadataCommand) -> Result[Document]:
        auth = require_permission(command.actor, "document:update")
        if auth.is_failure:
            return Result.fail(auth.error)  # type: ignore[arg-type]
        scope = _scope(command)
        async with KnowledgeUnitOfWork(self._session_factory) as uow:
            document = await uow.documents.get_scoped(
                scope, command.knowledge_base_id, command.document_id
            )
            if document is None:
                return Result.fail(not_found("Document").error)  # type: ignore[arg-type]
            if document.status in {DocumentStatus.ARCHIVED, DocumentStatus.DELETED}:
                return Result.fail(conflict("Document is not mutable").error)  # type: ignore[arg-type]
            if (
                command.expected_version is not None
                and document.row_version != command.expected_version
            ):
                return Result.fail(conflict("Version conflict").error)  # type: ignore[arg-type]
            if command.title is not None:
                document.title = command.title.strip()
            if command.declared_language is not None:
                document.declared_language = command.declared_language
            if command.classification_label is not None:
                document.classification_label = command.classification_label
            if command.tags is not None:
                document.tags = command.tags
            if command.metadata is not None:
                document.metadata_json = command.metadata
            document.updated_by_user_id = command.actor.user_id
            document.row_version += 1
            await uow.commit()
            return Result.ok(document)
