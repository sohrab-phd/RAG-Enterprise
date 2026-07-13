"""Unit of Work tests."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.db.repositories import SQLAlchemyRepository
from rag_enterprise.db.unit_of_work import SQLAlchemyUnitOfWork
from tests.db.support import SampleRecord


@pytest.mark.asyncio
async def test_unit_of_work_commits_on_success(
    session_factory: async_sessionmaker[AsyncSession],
    sample_record: SampleRecord,
) -> None:
    async with SQLAlchemyUnitOfWork(session_factory) as unit_of_work:
        repository = SQLAlchemyRepository(unit_of_work.session, SampleRecord)
        created = await repository.add(sample_record)
        await unit_of_work.commit()
        created_id = created.id

    async with SQLAlchemyUnitOfWork(session_factory) as unit_of_work:
        repository = SQLAlchemyRepository(unit_of_work.session, SampleRecord)
        loaded = await repository.get(created_id)
        assert loaded is not None


@pytest.mark.asyncio
async def test_unit_of_work_rolls_back_on_failure(
    session_factory: async_sessionmaker[AsyncSession],
    sample_record: SampleRecord,
) -> None:
    created_id: uuid.UUID

    with pytest.raises(RuntimeError, match="boom"):
        async with SQLAlchemyUnitOfWork(session_factory) as unit_of_work:
            repository = SQLAlchemyRepository(unit_of_work.session, SampleRecord)
            created = await repository.add(sample_record)
            created_id = created.id
            raise RuntimeError("boom")

    async with SQLAlchemyUnitOfWork(session_factory) as unit_of_work:
        repository = SQLAlchemyRepository(unit_of_work.session, SampleRecord)
        assert await repository.get(created_id) is None


@pytest.mark.asyncio
async def test_unit_of_work_bind_session_reuses_existing_session(
    session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    sample_record: SampleRecord,
) -> None:
    unit_of_work = SQLAlchemyUnitOfWork(session_factory).bind_session(session)
    repository = SQLAlchemyRepository(unit_of_work.session, SampleRecord)
    created = await repository.add(sample_record)
    assert created.id is not None
