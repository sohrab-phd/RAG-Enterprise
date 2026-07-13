"""Audit field mixin."""

import uuid

from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column


class AuditMixin:
    """Actor attribution for create and update operations."""

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
