"""LLM provider adapters and factory."""

from rag_enterprise.generation.providers.api import APIProvider
from rag_enterprise.generation.providers.factory import (
    create_llm_provider,
    create_llm_provider_sync,
    describe_llm_runtime,
    probe_llm_provider,
)
from rag_enterprise.generation.providers.local import LocalProvider
from rag_enterprise.generation.providers.mock import MockProvider
from rag_enterprise.generation.providers.ollama import OllamaProvider, OllamaStartupError
from rag_enterprise.generation.providers.openai_compatible import (
    OpenAICompatibleLLMProvider,
    OpenAICompatibleProvider,
)
from rag_enterprise.generation.providers.types import (
    CompletionResult,
    LLMRuntimeInfo,
    OllamaHealthSnapshot,
)

__all__ = [
    "APIProvider",
    "CompletionResult",
    "LLMRuntimeInfo",
    "LocalProvider",
    "MockProvider",
    "OllamaHealthSnapshot",
    "OllamaProvider",
    "OllamaStartupError",
    "OpenAICompatibleLLMProvider",
    "OpenAICompatibleProvider",
    "create_llm_provider",
    "create_llm_provider_sync",
    "describe_llm_runtime",
    "probe_llm_provider",
]
