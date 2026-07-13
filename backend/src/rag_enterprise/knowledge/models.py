"""Knowledge management ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from rag_enterprise.db.base import ModelBase
from rag_enterprise.db.mixins import (
    AuditMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
    WorkspaceTenantMixin,
)
from rag_enterprise.knowledge.enums import (
    ClassificationLabel,
    DocumentSourceType,
    DocumentStatus,
    ExtractionMethod,
    FolderStatus,
    KnowledgeBaseStatus,
    ProcessingStatus,
    UploadSessionStatus,
    VisibilityPolicy,
)


class KnowledgeBase(
    UUIDPrimaryKeyMixin,
    WorkspaceTenantMixin,
    TimestampMixin,
    SoftDeleteMixin,
    AuditMixin,
    VersionMixin,
    ModelBase,
):
    """Curated corpus boundary within a workspace."""

    __tablename__ = "knowledge_base"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_knowledge_base_workspace_name"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=KnowledgeBaseStatus.DRAFT
    )
    default_language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    visibility_policy: Mapped[str] = mapped_column(
        String(32), nullable=False, default=VisibilityPolicy.WORKSPACE
    )
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    folders: Mapped[list[Folder]] = relationship(back_populates="knowledge_base")
    documents: Mapped[list[Document]] = relationship(back_populates="knowledge_base")


class Folder(
    UUIDPrimaryKeyMixin,
    WorkspaceTenantMixin,
    TimestampMixin,
    SoftDeleteMixin,
    AuditMixin,
    VersionMixin,
    ModelBase,
):
    """Hierarchical folder within a knowledge base."""

    __tablename__ = "folder"
    __table_args__ = (
        UniqueConstraint(
            "knowledge_base_id",
            "parent_folder_id",
            "name",
            name="uq_folder_sibling_name",
        ),
    )

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_base.id"),
        nullable=False,
        index=True,
    )
    parent_folder_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("folder.id"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=FolderStatus.ACTIVE)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    knowledge_base: Mapped[KnowledgeBase] = relationship(back_populates="folders")
    parent_folder: Mapped[Folder | None] = relationship(
        remote_side="Folder.id",
        back_populates="child_folders",
    )
    child_folders: Mapped[list[Folder]] = relationship(back_populates="parent_folder")
    documents: Mapped[list[Document]] = relationship(back_populates="folder")


class Document(
    UUIDPrimaryKeyMixin,
    WorkspaceTenantMixin,
    TimestampMixin,
    SoftDeleteMixin,
    AuditMixin,
    VersionMixin,
    ModelBase,
):
    """Logical knowledge asset."""

    __tablename__ = "document"

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_base.id"),
        nullable=False,
        index=True,
    )
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("folder.id"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=DocumentStatus.DRAFT)
    source_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DocumentSourceType.UPLOAD
    )
    declared_language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    classification_label: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ClassificationLabel.PUBLIC_INTERNAL
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    legal_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    knowledge_base: Mapped[KnowledgeBase] = relationship(back_populates="documents")
    folder: Mapped[Folder | None] = relationship(back_populates="documents")
    versions: Mapped[list[DocumentVersion]] = relationship(back_populates="document")


class DocumentVersion(
    UUIDPrimaryKeyMixin,
    WorkspaceTenantMixin,
    TimestampMixin,
    AuditMixin,
    ModelBase,
):
    """Immutable document content version."""

    __tablename__ = "document_version"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_version_number"),
    )

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_base.id"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document.id"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    extraction_method: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ExtractionMethod.NATIVE_TEXT
    )
    processing_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ProcessingStatus.UPLOADED
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_key_original: Mapped[str] = mapped_column(String(1024), nullable=False)
    storage_key_extracted: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    upload_session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("upload_session.id"),
        nullable=True,
        unique=True,
    )

    document: Mapped[Document] = relationship(back_populates="versions")


class UploadSession(
    UUIDPrimaryKeyMixin,
    WorkspaceTenantMixin,
    TimestampMixin,
    AuditMixin,
    ModelBase,
):
    """Staging upload session for document binaries."""

    __tablename__ = "upload_session"

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_base.id"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document.id"),
        nullable=True,
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=UploadSessionStatus.PENDING
    )
    storage_key_staging: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
