"""Chunk and Embedding ORM models plus indexing result DTOs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from rag_enterprise.db.base import ModelBase
from rag_enterprise.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceTenantMixin
from rag_enterprise.db.types import EmbeddingVector
from rag_enterprise.indexing.constants import DEFAULT_DIMENSIONS
from rag_enterprise.indexing.enums import ChunkStatus, IndexStatus


class Chunk(
    UUIDPrimaryKeyMixin,
    WorkspaceTenantMixin,
    TimestampMixin,
    ModelBase,
):
    """Retrieval unit derived from a document version."""

    __tablename__ = "chunk"
    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "sequence_number",
            name="uq_chunk_version_sequence",
        ),
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
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_version.id"),
        nullable=False,
        index=True,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str | None] = mapped_column(String(500), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="paragraph")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ChunkStatus.CREATED)
    chunking_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Embedding(
    UUIDPrimaryKeyMixin,
    WorkspaceTenantMixin,
    ModelBase,
):
    """Dense vector representation of a chunk for similarity retrieval."""

    __tablename__ = "embedding"
    __table_args__ = (
        UniqueConstraint(
            "chunk_id",
            "embedding_model_id",
            "generation",
            name="uq_embedding_chunk_model_generation",
        ),
    )

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chunk.id"),
        nullable=False,
        index=True,
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_version.id"),
        nullable=False,
        index=True,
    )
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_base.id"),
        nullable=False,
        index=True,
    )
    embedding_model_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    model_key: Mapped[str] = mapped_column(String(128), nullable=False)
    vector: Mapped[list[float]] = mapped_column(EmbeddingVector(DEFAULT_DIMENSIONS), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    generation: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    index_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=IndexStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IndexingResult(BaseModel):
    """Outcome of indexing a document version."""

    model_config = ConfigDict(frozen=True)

    document_version_id: uuid.UUID
    embedding_model_id: uuid.UUID
    embeddings_created: int = 0
    embeddings_skipped: int = 0
    embeddings_failed: int = 0
    warnings: list[str] = Field(default_factory=list)
