"""Knowledge API tests."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from rag_enterprise.main import create_app


@pytest.fixture
async def knowledge_client(knowledge_container, actor_headers: dict[str, str]) -> AsyncClient:
    app = create_app()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=actor_headers,
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_create_and_get_knowledge_base(
    knowledge_client: AsyncClient,
    workspace_id: uuid.UUID,
) -> None:
    create = await knowledge_client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases",
        json={"name": "Engineering Docs", "default_language": "en"},
    )
    assert create.status_code == 201
    body = create.json()
    assert body["success"] is True
    assert body["data"]["name"] == "Engineering Docs"
    kb_id = body["data"]["id"]

    get = await knowledge_client.get(f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}")
    assert get.status_code == 200
    assert get.json()["data"]["id"] == kb_id


@pytest.mark.asyncio
async def test_duplicate_knowledge_base_name_returns_conflict(
    knowledge_client: AsyncClient,
    workspace_id: uuid.UUID,
) -> None:
    payload = {"name": "Duplicate KB"}
    first = await knowledge_client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases",
        json=payload,
    )
    assert first.status_code == 201
    second = await knowledge_client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases",
        json=payload,
    )
    assert second.status_code == 409
    assert second.json()["success"] is False


@pytest.mark.asyncio
async def test_document_upload_flow(
    knowledge_client: AsyncClient,
    workspace_id: uuid.UUID,
) -> None:
    kb = await knowledge_client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases",
        json={"name": "Upload KB"},
    )
    kb_id = kb.json()["data"]["id"]
    doc = await knowledge_client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/documents",
        json={"title": "Handbook"},
    )
    assert doc.status_code == 201
    document_id = doc.json()["data"]["id"]

    content = b"hello knowledge"
    upload = await knowledge_client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/uploads",
        json={
            "file_name": "handbook.txt",
            "file_size_bytes": len(content),
            "mime_type": "text/plain",
            "document_id": document_id,
        },
    )
    assert upload.status_code == 201
    upload_id = upload.json()["data"]["id"]

    complete = await knowledge_client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/uploads/{upload_id}/complete",
        content=content,
    )
    assert complete.status_code == 200

    version = await knowledge_client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge-bases/{kb_id}/documents/{document_id}/versions",
        json={"upload_id": upload_id},
    )
    assert version.status_code == 201
    assert version.json()["data"]["version_number"] == 1


@pytest.mark.asyncio
async def test_missing_actor_headers_returns_401(workspace_id: uuid.UUID) -> None:
    app = create_app()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/workspaces/{workspace_id}/knowledge-bases")
    assert response.status_code == 401
