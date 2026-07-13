"""LLM provider interface."""

from __future__ import annotations

from typing import Protocol


class LLMCompletionRequest(Protocol):
    """Prompt payload for text generation."""

    @property
    def system_prompt(self) -> str | None:
        """Return the optional system prompt."""

    @property
    def user_prompt(self) -> str:
        """Return the user prompt."""


class LLMCompletionResponse(Protocol):
    """Generated text response from a model provider."""

    @property
    def content(self) -> str:
        """Return generated text content."""

    @property
    def model_key(self) -> str:
        """Return the model used for generation."""


class LLMProvider(Protocol):
    """Generate natural-language responses."""

    @property
    def model_key(self) -> str:
        """Return the provider model identifier."""

    async def complete(self, request: LLMCompletionRequest) -> LLMCompletionResponse:
        """Generate a completion for the given request."""
