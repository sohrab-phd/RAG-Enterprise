"""Ollama local LLM adapter — discovery, selection, and chat generation."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from rag_enterprise.application.interfaces.llm import LLMCompletionRequest
from rag_enterprise.generation.exceptions import GenerationTimeoutError, ModelUnavailableError
from rag_enterprise.generation.providers.local import LocalProvider
from rag_enterprise.generation.providers.types import (
    CompletionResult,
    LLMRuntimeInfo,
    OllamaHealthSnapshot,
)

logger = logging.getLogger(__name__)

_DEFAULT_TEMPERATURE = 0.0
_PING_PROMPT = "Reply with exactly: ok"


class OllamaStartupError(Exception):
    """Fatal configuration / discovery error for local Ollama (fail startup)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class OllamaProvider(LocalProvider):
    """LocalProvider implementation targeting the Ollama HTTP API."""

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model_key: str = "auto",
        timeout_seconds: float = 60.0,
        temperature: float = _DEFAULT_TEMPERATURE,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._requested_model_key = (model_key or "").strip() or "auto"
        self._timeout_seconds = timeout_seconds
        self._temperature = temperature
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout_seconds),
        )
        self._installed_models: tuple[str, ...] = ()
        self._selected_model: str | None = None
        self._selection_mode: str = "auto"
        self._ollama_version: str | None = None
        self._reachable = False
        self._init_detail = "not_initialized"
        self._initialized = False

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_key(self) -> str:
        return self._selected_model or self._requested_model_key

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds

    @property
    def selection_mode(self) -> str:
        return self._selection_mode

    @property
    def installed_models(self) -> tuple[str, ...]:
        return self._installed_models

    @property
    def selected_model(self) -> str | None:
        return self._selected_model

    @property
    def ollama_version(self) -> str | None:
        return self._ollama_version

    @property
    def is_reachable(self) -> bool:
        return self._reachable

    async def initialize(self) -> None:
        """Discover models and resolve selection. Fatal cases raise OllamaStartupError."""
        try:
            installed = await self._list_models()
        except ModelUnavailableError as exc:
            self._reachable = False
            self._init_detail = str(exc)
            self._initialized = True
            logger.error(
                "ollama_unreachable_at_startup",
                extra={"base_url": self._base_url, "detail": str(exc)},
            )
            # Degrade — FastAPI still starts; readiness will be NOT READY.
            return

        self._reachable = True
        self._installed_models = tuple(installed)
        if not installed:
            raise OllamaStartupError(
                "No Ollama models are installed.\n"
                f"Base URL: {self._base_url}\n"
                "Install a model, for example: ollama pull <model>\n"
                "Then restart the backend."
            )

        selected, mode, warning = select_ollama_model(
            requested=self._requested_model_key,
            installed=installed,
        )
        self._selected_model = selected
        self._selection_mode = mode
        self._init_detail = "ready"
        self._initialized = True
        try:
            self._ollama_version = await self._fetch_version()
        except ModelUnavailableError:
            self._ollama_version = None

        self.emit_startup_log()
        if warning:
            logger.warning("ollama_model_selection_warning\n%s", warning)

    def emit_startup_log(self) -> None:
        """Write the operator-facing LLM startup summary."""
        lines = [
            "--------------------------------------------",
            "LLM Backend",
            "local",
            "",
            "Provider",
            "ollama",
            "",
            "Base URL",
            self._base_url,
            "",
            "Installed Models",
            str(len(self._installed_models)),
            "",
            "Selected Model",
            self._selected_model or "(none)",
            "",
            "Selection Mode",
            self._selection_mode,
            "--------------------------------------------",
        ]
        logger.info("\n".join(lines))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def complete(self, request: LLMCompletionRequest) -> CompletionResult:
        if not self._selected_model:
            raise ModelUnavailableError(
                self._init_detail
                or "Ollama model is not configured. Check OLLAMA_BASE_URL and installed models."
            )
        messages = _build_chat_messages(request)
        payload: dict[str, Any] = {
            "model": self._selected_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self._temperature},
        }
        try:
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as exc:
            raise GenerationTimeoutError(
                f"Ollama chat timed out after {self._timeout_seconds}s"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ModelUnavailableError(_format_http_error(exc)) from exc
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(f"Ollama connection failed: {exc}") from exc
        except ValueError as exc:
            raise ModelUnavailableError(f"Ollama returned invalid JSON: {exc}") from exc

        content = _extract_chat_content(data)
        return CompletionResult(content=content, model_key=self._selected_model)

    async def health_probe(self, *, include_generation_ping: bool = True) -> OllamaHealthSnapshot:
        """Readiness probe: reachability, models, optional lightweight generation."""
        started = time.perf_counter()
        try:
            installed = await self._list_models()
        except ModelUnavailableError as exc:
            return OllamaHealthSnapshot(
                reachable=False,
                installed_models=(),
                selected_model=self._selected_model,
                response_time_ms=None,
                detail=str(exc),
                ollama_version=self._ollama_version,
            )

        self._installed_models = tuple(installed)
        self._reachable = True
        elapsed_ms = (time.perf_counter() - started) * 1000.0

        if not self._selected_model and installed:
            try:
                selected, mode, _ = select_ollama_model(
                    requested=self._requested_model_key,
                    installed=installed,
                )
                self._selected_model = selected
                self._selection_mode = mode
            except OllamaStartupError as exc:
                return OllamaHealthSnapshot(
                    reachable=True,
                    installed_models=tuple(installed),
                    selected_model=None,
                    response_time_ms=elapsed_ms,
                    detail=str(exc),
                    ollama_version=self._ollama_version,
                )

        if include_generation_ping and self._selected_model:
            ping_started = time.perf_counter()
            try:
                await self._generation_ping()
            except (ModelUnavailableError, GenerationTimeoutError) as exc:
                return OllamaHealthSnapshot(
                    reachable=True,
                    installed_models=tuple(installed),
                    selected_model=self._selected_model,
                    response_time_ms=(time.perf_counter() - ping_started) * 1000.0,
                    detail=f"generation ping failed: {exc}",
                    ollama_version=self._ollama_version,
                )
            elapsed_ms = (time.perf_counter() - ping_started) * 1000.0

        return OllamaHealthSnapshot(
            reachable=True,
            installed_models=tuple(installed),
            selected_model=self._selected_model,
            response_time_ms=elapsed_ms,
            detail="ok",
            ollama_version=self._ollama_version,
        )

    def runtime_info(self, *, backend: str = "local") -> LLMRuntimeInfo:
        return LLMRuntimeInfo(
            backend=backend,
            provider=self.provider_name,
            model=self.model_key,
            timeout_seconds=self._timeout_seconds,
            reachability="reachable" if self._reachable else "unreachable",
            latency_ms=None,
            selected_model=self._selected_model,
            installed_models=self._installed_models,
            selection_mode=self._selection_mode,
            ollama_version=self._ollama_version,
            base_url=self._base_url,
            detail=self._init_detail,
        )

    def models_inventory(self) -> dict[str, object]:
        return {
            "backend": "local",
            "provider": self.provider_name,
            "selection_mode": self._selection_mode,
            "selected_model": self._selected_model,
            "installed_models": list(self._installed_models),
            "base_url": self._base_url,
            "reachable": self._reachable,
            "ollama_version": self._ollama_version,
        }

    async def _list_models(self) -> list[str]:
        try:
            response = await self._client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as exc:
            raise ModelUnavailableError(
                f"Ollama tags timed out ({self._base_url}/api/tags)"
            ) from exc
        except httpx.ConnectError as exc:
            raise ModelUnavailableError(
                f"Ollama connection refused at {self._base_url}. Is Ollama installed and running?"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ModelUnavailableError(_format_http_error(exc)) from exc
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(f"Ollama /api/tags failed: {exc}") from exc
        except ValueError as exc:
            raise ModelUnavailableError(f"Ollama /api/tags returned invalid JSON: {exc}") from exc

        models_raw = data.get("models") if isinstance(data, dict) else None
        if not isinstance(models_raw, list):
            raise ModelUnavailableError("Ollama /api/tags payload missing models list")

        names: list[str] = []
        for item in models_raw:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("model")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
        return sorted(set(names))

    async def _fetch_version(self) -> str | None:
        try:
            response = await self._client.get("/api/version")
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError):
            return None
        if isinstance(data, dict):
            version = data.get("version")
            if isinstance(version, str) and version.strip():
                return version.strip()
        return None

    async def _generation_ping(self) -> None:
        assert self._selected_model is not None
        payload = {
            "model": self._selected_model,
            "messages": [{"role": "user", "content": _PING_PROMPT}],
            "stream": False,
            "options": {"temperature": 0.0},
        }
        try:
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as exc:
            raise GenerationTimeoutError("Ollama generation ping timed out") from exc
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(f"Ollama generation ping failed: {exc}") from exc
        _extract_chat_content(data)


def select_ollama_model(
    *,
    requested: str,
    installed: list[str],
) -> tuple[str, str, str | None]:
    """Return (selected_model, selection_mode, optional_warning)."""
    if not installed:
        raise OllamaStartupError("No Ollama models are installed.")

    key = (requested or "").strip() or "auto"
    if key.lower() == "auto":
        selected = sorted(installed)[0]
        warning: str | None = None
        if len(installed) > 1:
            listed = "\n".join(f"- {name}" for name in sorted(installed))
            warning = (
                "------------------------------------------------\n"
                "Multiple Ollama models detected.\n"
                "\n"
                "Installed:\n"
                f"{listed}\n"
                "\n"
                "Automatically selected:\n"
                f"{selected}\n"
                "\n"
                "For deterministic behaviour set\n"
                f"LLM_MODEL_KEY={selected}\n"
                "------------------------------------------------"
            )
        return selected, "auto", warning

    if key not in installed:
        listed = "\n".join(f"- {name}" for name in sorted(installed))
        raise OllamaStartupError(
            "Requested Ollama model is not installed.\n"
            f"Requested model: {key}\n"
            "\n"
            "Installed models:\n"
            f"{listed}\n"
            "\n"
            "How to fix:\n"
            f"  ollama pull {key}\n"
            "  or set LLM_MODEL_KEY to one of the installed models\n"
            "  or set LLM_MODEL_KEY=auto\n"
        )
    return key, "explicit", None


def _build_chat_messages(request: LLMCompletionRequest) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    system = request.system_prompt
    if isinstance(system, str) and system.strip():
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": request.user_prompt})
    return messages


def _ascii_strip(value: str) -> str:
    """Trim ASCII whitespace only — preserve ZWNJ and other Unicode spacing."""
    return value.strip(" \t\n\r\f\v")


def _extract_chat_content(data: object) -> str:
    if not isinstance(data, dict):
        raise ModelUnavailableError("Malformed Ollama chat response")
    message = data.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and _ascii_strip(content):
            return _ascii_strip(content)
    # Some builds may return a top-level response field for generate-compat.
    response = data.get("response")
    if isinstance(response, str) and _ascii_strip(response):
        return _ascii_strip(response)
    raise ModelUnavailableError("Empty or malformed Ollama chat content")


def _format_http_error(exc: httpx.HTTPStatusError) -> str:
    status = exc.response.status_code
    body = (exc.response.text or "").strip()
    snippet = body[:300] if body else "(empty body)"
    return f"Ollama HTTP {status}: {snippet}"
