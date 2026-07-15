"""Ollama local LLM adapter (structure only — generation lands in RC2.7)."""

from __future__ import annotations

from rag_enterprise.application.interfaces.llm import LLMCompletionRequest
from rag_enterprise.generation.exceptions import ModelUnavailableError
from rag_enterprise.generation.providers.local import LocalProvider
from rag_enterprise.generation.providers.types import CompletionResult


class OllamaProvider(LocalProvider):
    """V1 local provider targeting Ollama.

    Configuration and factory wiring land in RC2.6. Networked generate/list/discover
    calls are deferred to RC2.7 — ``complete`` is intentionally unavailable.
    """

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model_key: str = "auto",
        timeout_seconds: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_key = model_key
        self._timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_key(self) -> str:
        return self._model_key

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds

    async def complete(self, request: LLMCompletionRequest) -> CompletionResult:
        del request  # unused until RC2.7
        raise ModelUnavailableError(
            "Ollama generation is not implemented yet (scheduled for RC2.7). "
            "Use LLM_BACKEND=mock for tests or LLM_BACKEND=api for remote models."
        )
