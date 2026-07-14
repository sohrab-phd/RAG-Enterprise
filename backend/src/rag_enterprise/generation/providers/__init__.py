"""LLM provider adapters."""

from rag_enterprise.generation.providers.openai_compatible import (
    CompletionResult,
    OpenAICompatibleLLMProvider,
)

__all__ = ["CompletionResult", "OpenAICompatibleLLMProvider"]
