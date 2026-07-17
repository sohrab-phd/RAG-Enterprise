"""Knowledge management commands."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import Field

from rag_enterprise.application.commands.base import CommandBase
from rag_enterprise.application.common import Result
from rag_enterprise.knowledge.context import RequestActor
from rag_enterprise.knowledge.validation import (
    is_valid_language_code,
    is_valid_name,
    is_valid_tags,
    is_valid_title,
    metadata_size_ok,
)


class _ScopedCommand(CommandBase):
    actor: RequestActor
    workspace_id: uuid.UUID
    knowledge_base_id: uuid.UUID | None = None


class CreateKnowledgeBaseCommand(CommandBase):
    actor: RequestActor
    workspace_id: uuid.UUID
    name: str
    default_language: str = "en"
    visibility_policy: str = "workspace"
    description: str | None = None

    async def validate_command(self) -> Result[None]:
        if not is_valid_name(self.name):
            return self.validation_error("Invalid knowledge base name")
        if not is_valid_language_code(self.default_language):
            return self.validation_error("Invalid default language")
        return Result.ok(None)


class UpdateKnowledgeBaseCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID
    name: str | None = None
    default_language: str | None = None
    visibility_policy: str | None = None
    description: str | None = None
    expected_version: int | None = None

    async def validate_command(self) -> Result[None]:
        if self.name is not None and not is_valid_name(self.name):
            return self.validation_error("Invalid knowledge base name")
        if self.default_language is not None and not is_valid_language_code(self.default_language):
            return self.validation_error("Invalid default language")
        return Result.ok(None)


class PublishKnowledgeBaseCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID


class ArchiveKnowledgeBaseCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID


class RestoreKnowledgeBaseCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID


class DeleteKnowledgeBaseCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID


class CreateFolderCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID
    name: str
    parent_folder_id: uuid.UUID | None = None

    async def validate_command(self) -> Result[None]:
        if not is_valid_name(self.name):
            return self.validation_error("Invalid folder name")
        return Result.ok(None)


class MoveFolderCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID
    folder_id: uuid.UUID
    target_parent_folder_id: uuid.UUID | None = None
    expected_version: int | None = None


class DeleteFolderCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID
    folder_id: uuid.UUID


class CreateDocumentCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID
    title: str
    folder_id: uuid.UUID | None = None
    declared_language: str | None = None
    source_type: str = "upload"
    classification_label: str = "public_internal"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    async def validate_command(self) -> Result[None]:
        if not is_valid_title(self.title):
            return self.validation_error("Invalid document title")
        if not is_valid_tags(self.tags):
            return self.validation_error("Invalid tags")
        if not metadata_size_ok(self.metadata):
            return self.validation_error("Metadata exceeds size limit")
        if self.declared_language and not is_valid_language_code(self.declared_language):
            return self.validation_error("Invalid declared language")
        return Result.ok(None)


class MoveDocumentCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID
    document_id: uuid.UUID
    target_folder_id: uuid.UUID | None = None


class InitiateUploadCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID
    file_name: str
    file_size_bytes: int
    mime_type: str | None = None
    document_id: uuid.UUID | None = None
    checksum_sha256: str | None = None

    async def validate_command(self) -> Result[None]:
        from rag_enterprise.knowledge.validation import is_allowed_file

        if not is_allowed_file(self.file_name, self.file_size_bytes):
            return self.validation_error("Invalid upload file")
        return Result.ok(None)


class CompleteUploadCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID
    upload_id: uuid.UUID
    checksum_sha256: str | None = None
    content: bytes | None = None


class UploadDocumentVersionCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID
    document_id: uuid.UUID
    upload_id: uuid.UUID
    change_summary: str | None = None


class ArchiveDocumentCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID
    document_id: uuid.UUID


class RestoreDocumentCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID
    document_id: uuid.UUID


class DeleteDocumentCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID
    document_id: uuid.UUID


class UpdateDocumentMetadataCommand(_ScopedCommand):
    knowledge_base_id: uuid.UUID
    document_id: uuid.UUID
    title: str | None = None
    declared_language: str | None = None
    classification_label: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    expected_version: int | None = None

    async def validate_command(self) -> Result[None]:
        if self.title is not None and not is_valid_title(self.title):
            return self.validation_error("Invalid document title")
        if self.tags is not None and not is_valid_tags(self.tags):
            return self.validation_error("Invalid tags")
        if self.metadata is not None and not metadata_size_ok(self.metadata):
            return self.validation_error("Metadata exceeds size limit")
        if self.declared_language is not None and not is_valid_language_code(
            self.declared_language
        ):
            return self.validation_error("Invalid declared language")
        return Result.ok(None)
