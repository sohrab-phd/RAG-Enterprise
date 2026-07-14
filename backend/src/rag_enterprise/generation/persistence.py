"""Conversation and Message ORM models for short chat history."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rag_enterprise.db.base import ModelBase
from rag_enterprise.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceTenantMixin
from rag_enterprise.db.mixins.timestamps import utc_now
from rag_enterprise.generation.models import ConversationStatus


class Conversation(
    UUIDPrimaryKeyMixin,
    WorkspaceTenantMixin,
    TimestampMixin,
    ModelBase,
):
    """Workspace-scoped short-history chat session."""

    __tablename__ = "conversation"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_base.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ConversationStatus.ACTIVE
    )
    locale: Mapped[str | None] = mapped_column(String(16), nullable=True)

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        order_by="Message.created_at",
    )


class Message(
    UUIDPrimaryKeyMixin,
    WorkspaceTenantMixin,
    ModelBase,
):
    """Single conversation turn."""

    __tablename__ = "message"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversation.id"),
        nullable=False,
        index=True,
    )
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_base.id"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    generation_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    abstention_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_template_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
