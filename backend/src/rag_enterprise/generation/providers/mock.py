"""Mock LLM provider (deterministic echo — tests / offline demos only)."""

from __future__ import annotations

from rag_enterprise.application.interfaces.llm import LLMCompletionRequest
from rag_enterprise.generation.providers.types import CompletionResult


class MockProvider:
    """Deterministic grounded stub used when ``LLM_BACKEND=mock``.

    Preserves the historical ``echo`` completion behavior. Not a production default.
    """

    def __init__(self, *, model_key: str = "mock-echo", provider_name: str = "echo") -> None:
        self._model_key = model_key
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_key(self) -> str:
        return self._model_key

    async def complete(self, request: LLMCompletionRequest) -> CompletionResult:
        return CompletionResult(content=self._echo(request), model_key=self._model_key)

    def _echo(self, request: LLMCompletionRequest) -> str:
        user_prompt = request.user_prompt
        if "ABSTAIN" in (request.system_prompt or "") and "EVIDENCE" not in user_prompt:
            return "ABSTAIN: insufficient_evidence"
        if "[1]" in user_prompt or "\n[1]" in user_prompt or "] chunk_id=" in user_prompt:
            return "Based on the retrieved evidence, here is the answer. [1]"
        return "ABSTAIN: insufficient_evidence"
