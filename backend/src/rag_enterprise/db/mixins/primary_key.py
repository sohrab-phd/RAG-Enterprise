"""UUIDv7 primary key mixin."""

import uuid

from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column

from rag_enterprise.db.types import generate_uuid7


class UUIDPrimaryKeyMixin:
    """Primary key using application-generated UUIDv7 values."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=generate_uuid7,
    )
