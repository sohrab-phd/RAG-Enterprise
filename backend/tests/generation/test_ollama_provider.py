"""Ollama provider unit tests (mocked HTTP — no live daemon required)."""

from __future__ import annotations

import json

import httpx
import pytest

from rag_enterprise.generation.exceptions import ModelUnavailableError
from rag_enterprise.generation.providers.ollama import (
    OllamaProvider,
    OllamaStartupError,
    select_ollama_model,
)


class _Req:
    def __init__(self, system: str | None, user: str) -> None:
        self.system_prompt = system
        self.user_prompt = user


def _tags_response(names: list[str]) -> httpx.Response:
    payload = {"models": [{"name": name} for name in names]}
    return httpx.Response(200, json=payload)


def _chat_response(content: str) -> httpx.Response:
    return httpx.Response(200, json={"message": {"role": "assistant", "content": content}})


def _version_response(version: str = "0.6.0") -> httpx.Response:
    return httpx.Response(200, json={"version": version})


@pytest.mark.asyncio
async def test_reachable_discovery_and_auto_select_single_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/api/tags"):
            return _tags_response(["gemma4:e4b-it-qat"])
        if request.url.path.endswith("/api/version"):
            return _version_response()
        raise AssertionError(request.url.path)

    transport = httpx.MockTransport(handler)
    provider = OllamaProvider(base_url="http://ollama.test", model_key="auto")
    await provider._client.aclose()
    provider._client = httpx.AsyncClient(
        base_url="http://ollama.test",
        transport=transport,
        timeout=5.0,
    )
    await provider.initialize()
    assert provider.is_reachable is True
    assert provider.selected_model == "gemma4:e4b-it-qat"
    assert provider.selection_mode == "auto"
    assert provider.installed_models == ("gemma4:e4b-it-qat",)
    await provider.aclose()


@pytest.mark.asyncio
async def test_unreachable_ollama_degrades_without_raising() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    transport = httpx.MockTransport(handler)
    provider = OllamaProvider(base_url="http://ollama.test", model_key="auto")
    await provider._client.aclose()
    provider._client = httpx.AsyncClient(
        base_url="http://ollama.test",
        transport=transport,
        timeout=5.0,
    )
    await provider.initialize()
    assert provider.is_reachable is False
    with pytest.raises(ModelUnavailableError):
        await provider.complete(_Req(None, "سلام"))
    await provider.aclose()


@pytest.mark.asyncio
async def test_explicit_model_missing_fails_startup() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return _tags_response(["llama3.2", "qwen3"])

    transport = httpx.MockTransport(handler)
    provider = OllamaProvider(base_url="http://ollama.test", model_key="missing-model")
    await provider._client.aclose()
    provider._client = httpx.AsyncClient(
        base_url="http://ollama.test",
        transport=transport,
        timeout=5.0,
    )
    with pytest.raises(OllamaStartupError, match="Requested Ollama model"):
        await provider.initialize()
    await provider.aclose()


@pytest.mark.asyncio
async def test_explicit_model_ok_and_persian_chat() -> None:
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("/api/tags"):
            return _tags_response(["gemma4:e4b-it-qat", "llama3.2"])
        if request.url.path.endswith("/api/version"):
            return _version_response("0.9.0")
        if request.url.path.endswith("/api/chat"):
            body = json.loads(request.content.decode("utf-8"))
            assert body["model"] == "gemma4:e4b-it-qat"
            assert body["stream"] is False
            assert body["messages"][0]["role"] == "system"
            assert "مرخصی" in body["messages"][-1]["content"]
            return _chat_response("مرخصی استحقاقی ۲۰ روز است. [1]")
        raise AssertionError(request.url.path)

    transport = httpx.MockTransport(handler)
    provider = OllamaProvider(
        base_url="http://ollama.test",
        model_key="gemma4:e4b-it-qat",
    )
    await provider._client.aclose()
    provider._client = httpx.AsyncClient(
        base_url="http://ollama.test",
        transport=transport,
        timeout=5.0,
    )
    await provider.initialize()
    assert provider.selection_mode == "explicit"
    result = await provider.complete(
        _Req(
            "Answer in Persian.",
            "=== EVIDENCE ===\n[1]\nسیاست مرخصی چیست؟",
        )
    )
    assert "مرخصی" in result.content
    assert result.model_key == "gemma4:e4b-it-qat"
    await provider.aclose()


def test_auto_selects_first_alphabetically_with_warning_text() -> None:
    selected, mode, warning = select_ollama_model(
        requested="auto",
        installed=["qwen3", "gemma4:e4b-it-qat", "llama3.2"],
    )
    assert selected == "gemma4:e4b-it-qat"
    assert mode == "auto"
    assert warning is not None
    assert "Multiple Ollama models detected" in warning
    assert "gemma4:e4b-it-qat" in warning


def test_empty_model_key_treated_as_auto() -> None:
    selected, mode, warning = select_ollama_model(requested="", installed=["zeta", "alpha"])
    assert selected == "alpha"
    assert mode == "auto"
    assert warning is not None


@pytest.mark.asyncio
async def test_health_probe_reports_metrics() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/api/tags"):
            return _tags_response(["gemma4:e4b-it-qat"])
        if request.url.path.endswith("/api/chat"):
            return _chat_response("ok")
        if request.url.path.endswith("/api/version"):
            return _version_response()
        raise AssertionError(request.url.path)

    transport = httpx.MockTransport(handler)
    provider = OllamaProvider(base_url="http://ollama.test", model_key="auto")
    await provider._client.aclose()
    provider._client = httpx.AsyncClient(
        base_url="http://ollama.test",
        transport=transport,
        timeout=5.0,
    )
    await provider.initialize()
    snap = await provider.health_probe(include_generation_ping=True)
    assert snap.reachable is True
    assert snap.selected_model == "gemma4:e4b-it-qat"
    assert snap.installed_models == ("gemma4:e4b-it-qat",)
    assert snap.response_time_ms is not None
    assert snap.detail == "ok"
    await provider.aclose()


@pytest.mark.asyncio
async def test_persian_response_preserves_zwnj() -> None:
    zwnj = "\u200c"

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/api/tags"):
            return _tags_response(["m1"])
        if request.url.path.endswith("/api/version"):
            return _version_response()
        if request.url.path.endswith("/api/chat"):
            return _chat_response(f"می{zwnj}خواهم ")
        raise AssertionError(request.url.path)

    transport = httpx.MockTransport(handler)
    provider = OllamaProvider(base_url="http://ollama.test", model_key="m1")
    await provider._client.aclose()
    provider._client = httpx.AsyncClient(
        base_url="http://ollama.test",
        transport=transport,
        timeout=5.0,
    )
    await provider.initialize()
    result = await provider.complete(_Req(None, "سلام"))
    assert zwnj in result.content
    await provider.aclose()


@pytest.mark.asyncio
async def test_no_installed_models_fails_startup() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return _tags_response([])

    transport = httpx.MockTransport(handler)
    provider = OllamaProvider(base_url="http://ollama.test", model_key="auto")
    await provider._client.aclose()
    provider._client = httpx.AsyncClient(
        base_url="http://ollama.test",
        transport=transport,
        timeout=5.0,
    )
    with pytest.raises(OllamaStartupError, match="No Ollama models"):
        await provider.initialize()
    await provider.aclose()
