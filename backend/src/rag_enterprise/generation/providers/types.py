"""Shared LLM provider result types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CompletionResult:
    """Concrete LLM completion response."""

    content: str
    model_key: str


@dataclass(frozen=True)
class LLMRuntimeInfo:
    """Runtime description for health / system inventory."""

    backend: str
    provider: str
    model: str
    timeout_seconds: float
    reachability: str = "not_checked"
    latency_ms: float | None = None
    selected_model: str | None = None
    installed_models: tuple[str, ...] = ()
    selection_mode: str | None = None
    ollama_version: str | None = None
    base_url: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class OllamaHealthSnapshot:
    """Result of a local Ollama readiness probe."""

    reachable: bool
    installed_models: tuple[str, ...]
    selected_model: str | None
    response_time_ms: float | None
    detail: str
    ollama_version: str | None = None
    extras: dict[str, object] = field(default_factory=dict)
