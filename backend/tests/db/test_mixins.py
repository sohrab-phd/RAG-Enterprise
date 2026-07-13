"""Mixin tests."""

import uuid

import pytest
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from rag_enterprise.db.base import ModelBase
from rag_enterprise.db.mixins import (
    AuditMixin,
    OrganizationTenantMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
)
from rag_enterprise.db.session.transaction import transaction
from rag_enterprise.db.types import generate_uuid7


class MixinProbe(
    ModelBase,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    AuditMixin,
    VersionMixin,
    OrganizationTenantMixin,
):
    __tablename__ = "mixin_probe"

    label: Mapped[str] = mapped_column(String(50), nullable=False)


@pytest.fixture
async def mixin_probe_table(session: AsyncSession) -> None:
    connection = await session.connection()
    await connection.run_sync(ModelBase.metadata.create_all)


@pytest.mark.asyncio
async def test_uuid_primary_key_generated_on_insert(
    session: AsyncSession,
    mixin_probe_table: None,
    sample_organization_id: uuid.UUID,
) -> None:
    entity = MixinProbe(label="probe", organization_id=sample_organization_id)

    async with transaction(session):
        session.add(entity)

    assert entity.id is not None
    assert entity.id.version == 7


@pytest.mark.asyncio
async def test_timestamp_mixin_sets_created_and_updated_at(
    session: AsyncSession,
    mixin_probe_table: None,
    sample_organization_id: uuid.UUID,
) -> None:
    entity = MixinProbe(label="probe", organization_id=sample_organization_id)

    async with transaction(session):
        session.add(entity)

    assert entity.created_at is not None
    assert entity.updated_at is not None
    assert entity.created_at.tzinfo is not None


@pytest.mark.asyncio
async def test_version_mixin_defaults_to_one(
    session: AsyncSession,
    mixin_probe_table: None,
    sample_organization_id: uuid.UUID,
) -> None:
    entity = MixinProbe(label="probe", organization_id=sample_organization_id)

    async with transaction(session):
        session.add(entity)

    assert entity.row_version == 1


def test_generate_uuid7_returns_version_7_identifier() -> None:
    value = generate_uuid7()
    assert value.version == 7
