"""Retrieval API tests."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.core.dependencies.providers import AppContainer
from rag_enterprise.indexing.service import IndexingService
from rag_enterprise.main import create_app
from tests.helpers.rag_seed import seed_chunked_version


@pytest.fixture
async def retrieval_client(rag_container: AppContainer, actor_headers: dict[str, str]):
    app = create_app()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=actor_headers,
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_retrieve_endpoint(
    retrieval_client: AsyncClient,
    rag_session_factory: async_sessionmaker[AsyncSession],
    indexing_service: IndexingService,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    async with rag_session_factory() as session:
        kb, _, version, _ = await seed_chunked_version(
            session,
            org_id=org_id,
            workspace_id=workspace_id,
            texts=["سیاست استخدام و منابع انسانی سازمان"],
            languages=["fa"],
        )
        kb_id = kb.id
        version_id = version.id

    await indexing_service.index_document_version(version_id)

    response = await retrieval_client.post(
        f"/api/v1/workspaces/{workspace_id}/retrieve",
        json={
            "query": "سیاست استخدام",
            "knowledge_base_id": str(kb_id),
            "top_k": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["result_count"] >= 1
    assert body["data"]["results"][0]["chunk_id"]
    assert body["data"]["results"][0]["text"]


@pytest.mark.asyncio
async def test_retrieve_empty_query_validation(
    retrieval_client: AsyncClient,
    workspace_id: uuid.UUID,
) -> None:
    response = await retrieval_client.post(
        f"/api/v1/workspaces/{workspace_id}/retrieve",
        json={
            "query": "",
            "knowledge_base_id": str(uuid.uuid4()),
            "top_k": 5,
        },
    )
    assert response.status_code == 422
