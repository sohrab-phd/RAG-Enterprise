"""OpenAI-compatible remote LLM provider (API backend)."""

from __future__ import annotations

import asyncio

import httpx

from rag_enterprise.application.interfaces.llm import LLMCompletionRequest
from rag_enterprise.generation.exceptions import GenerationTimeoutError, ModelUnavailableError
from rag_enterprise.generation.providers.api import APIProvider
from rag_enterprise.generation.providers.types import CompletionResult


class OpenAICompatibleProvider(APIProvider):
    """HTTP chat-completions client for OpenAI-compatible APIs."""

    def __init__(
        self,
        *,
        model_key: str = "gpt-4o-mini",
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: float = 60.0,
        provider_name: str = "openai",
    ) -> None:
        self._model_key = model_key
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_key(self) -> str:
        return self._model_key

    async def complete(self, request: LLMCompletionRequest) -> CompletionResult:
        try:
            return await asyncio.wait_for(
                self._http_complete(request),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as exc:
            raise GenerationTimeoutError() from exc

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


# Backward-compatible name used by older tests / imports.
OpenAICompatibleLLMProvider = OpenAICompatibleProvider
