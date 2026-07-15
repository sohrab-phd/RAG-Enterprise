"""Central factory for LLM providers — sole construction site outside tests."""

from __future__ import annotations

from typing import Any

from rag_enterprise.application.interfaces.llm import LLMProvider
from rag_enterprise.core.config.settings import Settings
from rag_enterprise.generation.providers.mock import MockProvider
from rag_enterprise.generation.providers.ollama import OllamaProvider, OllamaStartupError
from rag_enterprise.generation.providers.openai_compatible import OpenAICompatibleProvider
from rag_enterprise.generation.providers.types import LLMRuntimeInfo


async def create_llm_provider(settings: Settings) -> LLMProvider:
    """Build the configured LLM adapter. Callers must not branch on backend."""
    backend = settings.llm_backend
    if backend == "local":
        return await _create_local_provider(settings)
    if backend == "api":
        return _create_api_provider(settings)
    if backend == "mock":
        return _create_mock_provider(settings)
    raise ValueError(f"Unsupported LLM backend: {backend!r}")


def create_llm_provider_sync(settings: Settings) -> LLMProvider:
    """Synchronous construction without network I/O (unit tests / mock / api)."""
    backend = settings.llm_backend
    if backend == "local":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model_key=settings.llm_model_key,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    if backend == "api":
        return _create_api_provider(settings)
    if backend == "mock":
        return _create_mock_provider(settings)
    raise ValueError(f"Unsupported LLM backend: {backend!r}")


def describe_llm_runtime(
    settings: Settings,
    provider: LLMProvider | None = None,
) -> LLMRuntimeInfo:
    """Describe the active LLM for inventory endpoints."""
    if provider is not None and hasattr(provider, "runtime_info"):
        info = provider.runtime_info(backend=settings.llm_backend)  # type: ignore[attr-defined]
        if isinstance(info, LLMRuntimeInfo):
            return info
    return LLMRuntimeInfo(
        backend=settings.llm_backend,
        provider=settings.llm_provider_name,
        model=settings.llm_model_key,
        timeout_seconds=settings.llm_timeout_seconds,
        reachability="not_checked",
        latency_ms=None,
        selected_model=settings.llm_model_key,
        installed_models=(),
        selection_mode=None,
        ollama_version=None,
        base_url=settings.ollama_base_url if settings.llm_backend == "local" else None,
    )


async def probe_llm_provider(provider: LLMProvider) -> dict[str, Any] | None:
    """Optional readiness probe — only local Ollama implements health_probe."""
    probe = getattr(provider, "health_probe", None)
    if probe is None:
        return None
    snapshot = await probe(include_generation_ping=True)
    return {
        "reachable": snapshot.reachable,
        "installed_models": list(snapshot.installed_models),
        "selected_model": snapshot.selected_model,
        "response_time_ms": snapshot.response_time_ms,
        "detail": snapshot.detail,
        "ollama_version": snapshot.ollama_version,
    }


async def _create_local_provider(settings: Settings) -> LLMProvider:
    if settings.local_provider != "ollama":
        raise ValueError(f"Unsupported LOCAL_PROVIDER: {settings.local_provider!r}")
    provider = OllamaProvider(
        base_url=settings.ollama_base_url,
        model_key=settings.llm_model_key,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    try:
        await provider.initialize()
    except OllamaStartupError:
        await provider.aclose()
        raise
    return provider


def _create_api_provider(settings: Settings) -> LLMProvider:
    if settings.api_provider != "openai":
        raise ValueError(f"Unsupported API_PROVIDER: {settings.api_provider!r}")
    base_url = (settings.resolved_openai_base_url or "").strip()
    if not base_url:
        raise ValueError("OPENAI_BASE_URL is required when LLM_BACKEND=api")
    return OpenAICompatibleProvider(
        model_key=settings.llm_model_key,
        base_url=base_url,
        api_key=settings.resolved_openai_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
        provider_name=settings.api_provider,
    )


def _create_mock_provider(settings: Settings) -> LLMProvider:
    if settings.mock_provider != "echo":
        raise ValueError(f"Unsupported MOCK_PROVIDER: {settings.mock_provider!r}")
    return MockProvider(model_key=settings.llm_model_key, provider_name=settings.mock_provider)
