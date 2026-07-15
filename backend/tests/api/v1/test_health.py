"""RC1.2 operational health endpoint tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_enterprise.core.config.settings import get_settings
from rag_enterprise.db.base import ModelBase
from rag_enterprise.main import create_app


@pytest.fixture
async def live_client() -> AsyncIterator[AsyncClient]:
    """HTTP client without lifespan (liveness must not need DI)."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def ready_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    """HTTP client with lifespan using sqlite + local evaluation storage."""
    eval_root = tmp_path / "eval-artifacts"
    upload_root = tmp_path / "storage" / "uploads"
    monkeypatch.setenv("EVALUATION_STORAGE_ROOT", str(eval_root))
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(upload_root))
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("LLM_BACKEND", "mock")
    monkeypatch.setenv("EMBEDDING_BACKEND", "deterministic")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()

    app = create_app()
    async with app.router.lifespan_context(app):
        # Ensure count tables exist for /system inventory on sqlite.
        from rag_enterprise.core.dependencies.providers import get_container

        container = get_container()
        assert container.engine is not None
        await _create_schema(container.engine)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    get_settings.cache_clear()


async def _create_schema(engine: AsyncEngine) -> None:
    # Import models so metadata is populated.
    import rag_enterprise.indexing.models  # noqa: F401
    import rag_enterprise.knowledge.models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(ModelBase.metadata.create_all)


@pytest.mark.asyncio
async def test_live_returns_immediately(live_client: AsyncClient) -> None:
    response = await live_client.get("/api/v1/live")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "live"
    assert "timestamp" in payload


@pytest.mark.asyncio
async def test_ready_not_ready_without_lifespan(live_client: AsyncClient) -> None:
    response = await live_client.get("/api/v1/ready")
    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    names = {item["name"] for item in payload["checks"]}
    assert "configuration" in names
    assert "dependency_injection" in names


@pytest.mark.asyncio
async def test_ready_ok_with_lifespan(ready_client: AsyncClient) -> None:
    response = await ready_client.get("/api/v1/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert all(item["ok"] for item in payload["checks"])
    check_names = {item["name"] for item in payload["checks"]}
    assert check_names == {
        "configuration",
        "dependency_injection",
        "database",
        "evaluation_storage",
        "upload_storage",
    }
    upload = next(item for item in payload["checks"] if item["name"] == "upload_storage")
    assert "filesystem" in upload["detail"]


@pytest.mark.asyncio
async def test_system_inventory(ready_client: AsyncClient) -> None:
    response = await ready_client.get("/api/v1/system")
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"]
    assert payload["environment"] == "test"
    assert payload["providers"]["llm"]["mode"] == "mock"
    assert payload["providers"]["llm"]["backend"] == "mock"
    assert payload["providers"]["llm"]["provider"] == "echo"
    assert payload["providers"]["llm"]["reachability"] == "not_checked"
    assert payload["llm"]["backend"] == "mock"
    assert payload["llm"]["provider"] == "echo"
    assert payload["llm"]["model"]
    assert payload["llm"]["selected_model"]
    assert payload["llm"]["timeout_seconds"] == 60.0
    assert isinstance(payload["llm"]["installed_models"], list)
    assert payload["providers"]["embedding"]["mode"] == "deterministic"
    assert payload["models"]["llm_model_key"]
    assert payload["models"]["embedding_model_key"]
    assert payload["models"]["prompt_template_version"] == "v1"
    assert payload["counts"]["documents"] == 0
    assert payload["counts"]["chunks"] == 0
    assert payload["counts"]["embeddings"] == 0
    assert payload["counts"]["evaluation_runs"] == 0
    assert payload["counts"]["ok"] is True
    assert payload["configuration_validated"] is True
    assert payload["dependency_injection_initialized"] is True


@pytest.mark.asyncio
async def test_system_models_catalog(ready_client: AsyncClient) -> None:
    response = await ready_client.get("/api/v1/system/models")
    assert response.status_code == 200
    payload = response.json()
    assert payload["backend"] == "mock"
    assert payload["provider"] == "echo"
    assert payload["selected_model"]
    assert isinstance(payload["installed_models"], list)


@pytest.mark.asyncio
async def test_system_not_ready_without_di(live_client: AsyncClient) -> None:
    response = await live_client.get("/api/v1/system")
    assert response.status_code == 503
    payload = response.json()
    assert payload["dependency_injection_initialized"] is False


@pytest.mark.asyncio
async def test_legacy_health_still_works(live_client: AsyncClient) -> None:
    response = await live_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_ready_openapi_documented(ready_client: AsyncClient) -> None:
    response = await ready_client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/live" in paths
    assert "/api/v1/ready" in paths
    assert "/api/v1/system" in paths
    assert "/api/v1/system/models" in paths
