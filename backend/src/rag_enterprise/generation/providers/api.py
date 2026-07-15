"""API LLM provider category (remote OpenAI-compatible HTTP APIs)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from rag_enterprise.application.interfaces.llm import LLMCompletionRequest, LLMCompletionResponse


class APIProvider(ABC):
    """Base for remote API execution backends."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Concrete API engine identifier (for example ``openai``)."""

    @property
    @abstractmethod
    def model_key(self) -> str:
        """Configured model identifier."""

    @abstractmethod
    async def complete(self, request: LLMCompletionRequest) -> LLMCompletionResponse:
        """Generate a completion."""
