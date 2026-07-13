"""Repository base tests."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_enterprise.db.mixins.timestamps import utc_now
from rag_enterprise.db.repositories import SQLAlchemyRepository
from rag_enterprise.db.session.transaction import transaction
from tests.db.support import SampleRecord, build_sample_record


@pytest.mark.asyncio
async def test_repository_add_get_exists(
    session: AsyncSession,
    sample_record: SampleRecord,
) -> None:
    repository = SQLAlchemyRepository(session, SampleRecord)

    async with transaction(session):
        created = await repository.add(sample_record)

    assert created.id is not None
    assert await repository.exists(created.id)

    loaded = await repository.get(created.id)
    assert loaded is not None
    assert loaded.name == "sample"


@pytest.mark.asyncio
async def test_repository_list_returns_records(
    session: AsyncSession,
    sample_record: SampleRecord,
) -> None:
    repository = SQLAlchemyRepository(session, SampleRecord)

    async with transaction(session):
        await repository.add(sample_record)
        second = build_sample_record(
            organization_id=sample_record.organization_id,
            workspace_id=sample_record.workspace_id,
            name="second",
        )
        await repository.add(second)

    records = await repository.list()
    assert len(records) == 2


@pytest.mark.asyncio
async def test_repository_excludes_soft_deleted_by_default(
    session: AsyncSession,
    sample_record: SampleRecord,
) -> None:
    repository = SQLAlchemyRepository(session, SampleRecord)

    async with transaction(session):
        created = await repository.add(sample_record)
        created.deleted_at = utc_now()
        await session.flush()

    assert not await repository.exists(created.id)
    assert await repository.exists(created.id, include_deleted=True)
    assert await repository.get(created.id) is None


@pytest.mark.asyncio
async def test_repository_remove_deletes_entity(
    session: AsyncSession,
    sample_record: SampleRecord,
) -> None:
    repository = SQLAlchemyRepository(session, SampleRecord)

    async with transaction(session):
        created = await repository.add(sample_record)
        await repository.remove(created)

    assert not await repository.exists(created.id, include_deleted=True)


@pytest.mark.asyncio
async def test_repository_get_returns_none_for_missing_id(session: AsyncSession) -> None:
    repository = SQLAlchemyRepository(session, SampleRecord)
    assert await repository.get(uuid.uuid4()) is None
