"""Local LLM provider category (runs on the operator machine / intranet)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from rag_enterprise.application.interfaces.llm import LLMCompletionRequest, LLMCompletionResponse


class LocalProvider(ABC):
    """Base for local execution backends (Ollama, …)."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Concrete local engine identifier (for example ``ollama``)."""

    @property
    @abstractmethod
    def model_key(self) -> str:
        """Configured model identifier."""

    @abstractmethod
    async def complete(self, request: LLMCompletionRequest) -> LLMCompletionResponse:
        """Generate a completion."""
