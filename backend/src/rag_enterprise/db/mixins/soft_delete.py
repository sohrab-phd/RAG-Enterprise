"""Soft delete mixin."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column


class SoftDeleteMixin:
    """Soft deletion metadata. Active rows have ``deleted_at IS NULL``."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    delete_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
