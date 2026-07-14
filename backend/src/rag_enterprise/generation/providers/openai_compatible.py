"""OpenAI-compatible LLM provider adapter."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Literal

import httpx

from rag_enterprise.application.interfaces.llm import LLMCompletionRequest
from rag_enterprise.generation.exceptions import GenerationTimeoutError, ModelUnavailableError


@dataclass(frozen=True)
class CompletionResult:
    """Concrete LLM completion response."""

    content: str
    model_key: str


class OpenAICompatibleLLMProvider:
    """LLMProvider using an OpenAI-compatible chat completions API.

    Modes:
    - ``echo``: deterministic local response for tests (cites [1] from evidence)
    - ``http``: POST to ``{base_url}/chat/completions``
    """

    def __init__(
        self,
        *,
        mode: Literal["echo", "http"] = "echo",
        model_key: str = "gpt-4o-mini",
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._mode = mode
        self._model_key = model_key
        self._base_url = (base_url or "").rstrip("/")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    @property
    def model_key(self) -> str:
        return self._model_key

    async def complete(self, request: LLMCompletionRequest) -> CompletionResult:
        if self._mode == "echo":
            return CompletionResult(content=self._echo(request), model_key=self._model_key)
        try:
            return await asyncio.wait_for(
                self._http_complete(request),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as exc:
            raise GenerationTimeoutError() from exc

    def _echo(self, request: LLMCompletionRequest) -> str:
        user_prompt = request.user_prompt
        if "ABSTAIN" in (request.system_prompt or "") and "EVIDENCE" not in user_prompt:
            return "ABSTAIN: insufficient_evidence"
        # Prefer citing the first evidence marker when present.
        if "[1]" in user_prompt or "\n[1]" in user_prompt or "] chunk_id=" in user_prompt:
            # Extract a short snippet after first evidence block if possible.
            return "Based on the retrieved evidence, here is the answer. [1]"
        return "ABSTAIN: insufficient_evidence"

    async def _http_complete(self, request: LLMCompletionRequest) -> CompletionResult:
        if not self._base_url:
            raise ModelUnavailableError("LLM base URL is not configured")
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.user_prompt})
        payload = {
            "model": self._model_key,
            "messages": messages,
            "temperature": 0.0,
        }
        url = f"{self._base_url}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise GenerationTimeoutError() from exc
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(str(exc)) from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelUnavailableError("Malformed LLM response") from exc
        if not isinstance(content, str) or not content.strip():
            raise ModelUnavailableError("Empty LLM response")
        return CompletionResult(content=content.strip(), model_key=self._model_key)
