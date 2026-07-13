"""Knowledge management domain enumerations."""

from enum import StrEnum


class KnowledgeBaseStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    REINDEXING = "reindexing"
    ARCHIVED = "archived"
    DELETED = "deleted"


class VisibilityPolicy(StrEnum):
    PRIVATE = "private"
    WORKSPACE = "workspace"
    ORGANIZATION = "organization"


class FolderStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class DocumentSourceType(StrEnum):
    UPLOAD = "upload"
    CONNECTOR = "connector"
    URL = "url"


class ClassificationLabel(StrEnum):
    PUBLIC_INTERNAL = "public_internal"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"
    REGULATED = "regulated"


class ExtractionMethod(StrEnum):
    NATIVE_TEXT = "native_text"
    OCR = "ocr"
    CONNECTOR_IMPORT = "connector_import"
    MANUAL_EDIT = "manual_edit"


class ProcessingStatus(StrEnum):
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    CHUNKING = "chunking"
    CHUNKED = "chunked"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class UploadSessionStatus(StrEnum):
    PENDING = "pending"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
