"""RC2.6 LLM provider factory smoke tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from rag_enterprise.core.config.database import DatabaseSettings
from rag_enterprise.core.config.settings import Settings
from rag_enterprise.generation.providers import (
    MockProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    create_llm_provider,
    describe_llm_runtime,
)


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_name": "RAG-enterprise",
        "app_env": "test",
        "app_debug": False,
        "log_level": "INFO",
        "api_v1_prefix": "/api/v1",
        "backend_host": "0.0.0.0",
        "backend_port": 8000,
        "database": DatabaseSettings(
            url="sqlite+aiosqlite:///:memory:",
            host="localhost",
            port=5432,
            user="rag",
            password="rag",
            name="rag_enterprise",
        ),
        "embedding_backend": "deterministic",
        "embedding_model_key": "BAAI/bge-m3",
        "embedding_dimensions": 1024,
        "embedding_batch_size": 32,
        "retrieval_default_top_k": 8,
        "llm_backend": "mock",
        "local_provider": "ollama",
        "api_provider": "openai",
        "mock_provider": "echo",
        "ollama_base_url": "http://localhost:11434",
        "openai_base_url": None,
        "openai_api_key": None,
        "llm_base_url": None,
        "llm_api_key": None,
        "llm_model_key": "auto",
        "llm_timeout_seconds": 60.0,
        "llm_legacy_backend": None,
        "generation_min_evidence_score": 0.25,
        "generation_max_history_messages": 6,
        "evaluation_storage_root": "eval-artifacts-test",
        "file_storage_root": "storage/uploads",
        "upload_max_file_size_bytes": 1024,
        "upload_max_bulk_files": 10,
        "upload_session_ttl_hours": 24,
    }
    values.update(overrides)
    return Settings.model_construct(**values)


def test_factory_selects_mock_provider() -> None:
    provider = create_llm_provider(_settings(llm_backend="mock", llm_model_key="mock-echo"))
    assert isinstance(provider, MockProvider)
    assert provider.provider_name == "echo"


def test_factory_selects_ollama_for_local() -> None:
    provider = create_llm_provider(_settings(llm_backend="local", llm_model_key="auto"))
    assert isinstance(provider, OllamaProvider)
    assert provider.provider_name == "ollama"
    assert provider.base_url == "http://localhost:11434"


def test_factory_selects_openai_compatible_for_api() -> None:
    provider = create_llm_provider(
        _settings(
            llm_backend="api",
            llm_model_key="gpt-4o-mini",
            openai_base_url="https://api.example.com/v1",
            openai_api_key="sk-test",
        )
    )
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.provider_name == "openai"
    assert provider.model_key == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_ollama_complete_is_not_implemented_yet() -> None:
    provider = create_llm_provider(_settings(llm_backend="local"))
    from rag_enterprise.generation.exceptions import ModelUnavailableError

    class _Req:
        system_prompt = None
        user_prompt = "hello"

    with pytest.raises(ModelUnavailableError, match="RC2.7"):
        await provider.complete(_Req())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_mock_echo_behavior_preserved() -> None:
    provider = create_llm_provider(_settings(llm_backend="mock"))

    class _Req:
        system_prompt = "Answer with citations."
        user_prompt = "=== EVIDENCE ===\n[1] chunk_id=abc\ntext: hi"

    result = await provider.complete(_Req())  # type: ignore[arg-type]
    assert "[1]" in result.content


def test_describe_runtime_config_only() -> None:
    info = describe_llm_runtime(_settings(llm_backend="local", llm_model_key="auto"))
    assert info.backend == "local"
    assert info.provider == "ollama"
    assert info.model == "auto"
    assert info.reachability == "not_checked"
    assert info.latency_ms is None


def test_settings_legacy_echo_maps_to_mock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BACKEND", "echo")
    monkeypatch.setenv("EVALUATION_STORAGE_ROOT", str(tmp_path / "eval"))
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    from rag_enterprise.core.config.settings import get_settings

    get_settings.cache_clear()
    settings = Settings()
    assert settings.llm_backend == "mock"
    assert settings.llm_legacy_backend == "echo"
    get_settings.cache_clear()


def test_settings_legacy_http_maps_to_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BACKEND", "http")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.example.com/v1")
    monkeypatch.setenv("LLM_API_KEY", "sk-legacy")
    monkeypatch.setenv("EVALUATION_STORAGE_ROOT", str(tmp_path / "eval"))
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    from rag_enterprise.core.config.settings import get_settings

    get_settings.cache_clear()
    settings = Settings()
    assert settings.llm_backend == "api"
    assert settings.llm_legacy_backend == "http"
    assert settings.resolved_openai_base_url == "https://api.example.com/v1"
    assert settings.resolved_openai_api_key == "sk-legacy"
    get_settings.cache_clear()
