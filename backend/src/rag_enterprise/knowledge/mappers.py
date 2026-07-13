"""Map ORM entities to DTOs."""

from __future__ import annotations

import uuid

from rag_enterprise.knowledge.dto import (
    DocumentDetailDTO,
    DocumentSummaryDTO,
    DocumentVersionSummaryDTO,
    FolderSummaryDTO,
    KnowledgeBaseDetailDTO,
    KnowledgeBaseSummaryDTO,
    UploadSessionDTO,
)
from rag_enterprise.knowledge.models import (
    Document,
    DocumentVersion,
    Folder,
    KnowledgeBase,
    UploadSession,
)


def to_kb_summary(entity: KnowledgeBase) -> KnowledgeBaseSummaryDTO:
    return KnowledgeBaseSummaryDTO(
        id=entity.id,
        name=entity.name,
        status=entity.status,
        default_language=entity.default_language,
        visibility_policy=entity.visibility_policy,
        document_count=entity.document_count,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def to_kb_detail(entity: KnowledgeBase) -> KnowledgeBaseDetailDTO:
    return KnowledgeBaseDetailDTO(
        **to_kb_summary(entity).model_dump(),
        description=entity.description,
        version=entity.row_version,
    )


def to_folder_summary(entity: Folder) -> FolderSummaryDTO:
    return FolderSummaryDTO(
        id=entity.id,
        name=entity.name,
        parent_folder_id=entity.parent_folder_id,
        path=entity.path,
        depth=entity.depth,
        status=entity.status,
        version=entity.row_version,
    )


def to_document_summary(entity: Document) -> DocumentSummaryDTO:
    return DocumentSummaryDTO(
        id=entity.id,
        title=entity.title,
        status=entity.status,
        folder_id=entity.folder_id,
        declared_language=entity.declared_language,
        classification_label=entity.classification_label,
        current_version_id=entity.current_version_id,
        updated_at=entity.updated_at,
    )


def to_document_detail(entity: Document) -> DocumentDetailDTO:
    return DocumentDetailDTO(
        **to_document_summary(entity).model_dump(),
        source_type=entity.source_type,
        tags=list(entity.tags),
        metadata=dict(entity.metadata_json),
        legal_hold=entity.legal_hold,
        version=entity.row_version,
        created_at=entity.created_at,
    )


def to_version_summary(
    entity: DocumentVersion,
    *,
    current_version_id: uuid.UUID | None,
) -> DocumentVersionSummaryDTO:
    return DocumentVersionSummaryDTO(
        id=entity.id,
        version_number=entity.version_number,
        extraction_method=entity.extraction_method,
        processing_status=entity.processing_status,
        content_hash=entity.content_hash,
        file_name=entity.file_name,
        file_size_bytes=entity.file_size_bytes,
        mime_type=entity.mime_type,
        is_current=entity.id == current_version_id,
        created_at=entity.created_at,
    )


def to_upload_session(entity: UploadSession) -> UploadSessionDTO:
    return UploadSessionDTO(
        id=entity.id,
        status=entity.status,
        file_name=entity.file_name,
        file_size_bytes=entity.file_size_bytes,
        expires_at=entity.expires_at,
    )
