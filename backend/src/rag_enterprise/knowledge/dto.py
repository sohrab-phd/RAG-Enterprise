"""Knowledge management DTOs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from rag_enterprise.application.dto.base import PaginationDTO, RequestDTO, ResponseDTO


class CreateKnowledgeBaseRequest(RequestDTO):
    name: str = Field(min_length=1, max_length=200)
    default_language: str = "en"
    visibility_policy: str = "workspace"
    description: str | None = Field(default=None, max_length=2000)


class UpdateKnowledgeBaseRequest(RequestDTO):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    default_language: str | None = None
    visibility_policy: str | None = None
    description: str | None = Field(default=None, max_length=2000)
    expected_version: int | None = None


class KnowledgeBaseSummaryDTO(ResponseDTO):
    id: uuid.UUID
    name: str
    status: str
    default_language: str
    visibility_policy: str
    document_count: int
    created_at: datetime
    updated_at: datetime


class KnowledgeBaseDetailDTO(KnowledgeBaseSummaryDTO):
    description: str | None
    version: int


class CreateFolderRequest(RequestDTO):
    name: str = Field(min_length=1, max_length=200)
    parent_folder_id: uuid.UUID | None = None


class MoveFolderRequest(RequestDTO):
    target_parent_folder_id: uuid.UUID | None = None
    expected_version: int | None = None


class FolderSummaryDTO(ResponseDTO):
    id: uuid.UUID
    name: str
    parent_folder_id: uuid.UUID | None
    path: str
    depth: int
    status: str
    version: int


class CreateDocumentRequest(RequestDTO):
    title: str = Field(min_length=1, max_length=500)
    folder_id: uuid.UUID | None = None
    declared_language: str | None = None
    source_type: str = "upload"
    classification_label: str = "public_internal"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateDocumentMetadataRequest(RequestDTO):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    declared_language: str | None = None
    classification_label: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    expected_version: int | None = None


class MoveDocumentRequest(RequestDTO):
    target_folder_id: uuid.UUID | None = None


class InitiateUploadRequest(RequestDTO):
    file_name: str = Field(min_length=1, max_length=500)
    file_size_bytes: int = Field(gt=0)
    mime_type: str | None = None
    document_id: uuid.UUID | None = None
    checksum_sha256: str | None = None


class CompleteUploadRequest(RequestDTO):
    checksum_sha256: str | None = None
    content: bytes | None = None


class CreateDocumentVersionRequest(RequestDTO):
    upload_id: uuid.UUID
    change_summary: str | None = Field(default=None, max_length=500)


class DocumentSummaryDTO(ResponseDTO):
    id: uuid.UUID
    title: str
    status: str
    folder_id: uuid.UUID | None
    declared_language: str
    classification_label: str
    current_version_id: uuid.UUID | None
    updated_at: datetime


class DocumentDetailDTO(DocumentSummaryDTO):
    source_type: str
    tags: list[str]
    metadata: dict[str, Any]
    legal_hold: bool
    version: int
    created_at: datetime


class DocumentVersionSummaryDTO(ResponseDTO):
    id: uuid.UUID
    version_number: int
    extraction_method: str
    processing_status: str
    content_hash: str
    file_name: str
    file_size_bytes: int
    mime_type: str
    is_current: bool
    created_at: datetime


class UploadSessionDTO(ResponseDTO):
    id: uuid.UUID
    status: str
    file_name: str
    file_size_bytes: int
    expires_at: datetime


class TreeFolderNodeDTO(ResponseDTO):
    id: uuid.UUID
    name: str
    status: str
    document_count: int
    children: list[TreeFolderNodeDTO] = Field(default_factory=list)


class TreeViewDTO(ResponseDTO):
    knowledge_base_id: uuid.UUID
    folders: list[TreeFolderNodeDTO]


class FolderContentsDTO(ResponseDTO):
    folder_id: uuid.UUID | None
    folders: list[FolderSummaryDTO]
    documents: list[DocumentSummaryDTO]
    pagination: PaginationDTO[DocumentSummaryDTO] | None = None
