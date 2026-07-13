"""Test-only persistence models."""

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from rag_enterprise.db.base import ModelBase
from rag_enterprise.db.mixins import (
    AuditMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
    WorkspaceTenantMixin,
)


class SampleRecord(
    ModelBase,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    AuditMixin,
    VersionMixin,
    WorkspaceTenantMixin,
):
    """Test-only model used to validate persistence infrastructure."""

    __tablename__ = "sample_records"

    name: Mapped[str] = mapped_column(String(100), nullable=False)


def build_sample_record(
    *,
    organization_id: uuid.UUID,
    workspace_id: uuid.UUID,
    name: str = "sample",
) -> SampleRecord:
    return SampleRecord(
        organization_id=organization_id,
        workspace_id=workspace_id,
        name=name,
        created_by_user_id=organization_id,
        updated_by_user_id=organization_id,
    )
