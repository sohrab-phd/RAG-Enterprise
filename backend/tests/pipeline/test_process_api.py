"""Process-and-index API tests."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from rag_enterprise.core.config.settings import get_settings
from rag_enterprise.core.dependencies.providers import get_container
from rag_enterprise.db.base import ModelBase
from rag_enterprise.main import create_app

ORG_ID = uuid.UUID("018f0000-0000-7000-8000-0000000000a1")
WORKSPACE_ID = uuid.UUID("018f0000-0000-7000-8000-0000000000a2")
USER_ID = uuid.UUID("018f0000-0000-7000-8000-0000000000a3")


@pytest.fixture
async def process_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    monkeypatch.setenv("EVALUATION_STORAGE_ROOT", str(tmp_path / "eval"))
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("LLM_BACKEND", "echo")
    monkeypatch.setenv("EMBEDDING_BACKEND", "deterministic")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()

    app = create_app()
    async with app.router.lifespan_context(app):
        container = get_container()
        assert container.engine is not None
        import rag_enterprise.generation.persistence  # noqa: F401
        import rag_enterprise.indexing.models  # noqa: F401
        import rag_enterprise.knowledge.models  # noqa: F401

        async with container.engine.begin() as connection:
            await connection.run_sync(ModelBase.metadata.create_all)

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={
                "X-Organization-Id": str(ORG_ID),
                "X-User-Id": str(USER_ID),
            },
        ) as client:
            yield client

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_process_and_index_document(process_client: AsyncClient) -> None:
    base = f"/api/v1/workspaces/{WORKSPACE_ID}"
    kb = await process_client.post(
        f"{base}/knowledge-bases",
        json={"name": "Process KB", "default_language": "fa"},
    )
    assert kb.status_code == 201
    kb_id = kb.json()["data"]["id"]
    published = await process_client.post(f"{base}/knowledge-bases/{kb_id}/publish")
    assert published.status_code == 200
    assert published.json()["data"]["status"] == "active"

    document = await process_client.post(
        f"{base}/knowledge-bases/{kb_id}/documents",
        json={"title": "Policy", "declared_language": "fa"},
    )
    document_id = document.json()["data"]["id"]
    content = (
        "مرخصی استحقاقی سالانه ۲۰ روز کاری است.\n\nدورکاری حداکثر دو روز در هفته است.".encode()
    )
    upload = await process_client.post(
        f"{base}/knowledge-bases/{kb_id}/uploads",
        json={
            "file_name": "policy.txt",
            "file_size_bytes": len(content),
            "mime_type": "text/plain",
            "document_id": document_id,
        },
    )
    upload_id = upload.json()["data"]["id"]
    await process_client.post(
        f"{base}/knowledge-bases/{kb_id}/uploads/{upload_id}/complete",
        content=content,
    )
    version = await process_client.post(
        f"{base}/knowledge-bases/{kb_id}/documents/{document_id}/versions",
        json={"upload_id": upload_id},
    )
    assert version.json()["data"]["processing_status"] == "uploaded"

    response = await process_client.post(f"{base}/documents/{document_id}/process")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["current_status"] == "indexed"
    assert data["processed_chunks"] >= 1
    assert data["indexed_embeddings"] >= 1
    assert isinstance(data["warnings"], list)

    again = await process_client.post(f"{base}/documents/{document_id}/process")
    assert again.status_code == 200
    assert again.json()["data"]["current_status"] == "indexed"
    assert "already_indexed" in again.json()["data"]["warnings"]
