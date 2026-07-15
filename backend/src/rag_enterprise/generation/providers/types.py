"""Shared LLM provider result types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompletionResult:
    """Concrete LLM completion response."""

    content: str
    model_key: str


@dataclass(frozen=True)
class LLMRuntimeInfo:
    """Config-only runtime description for health / system inventory (no probe calls)."""

    backend: str
    provider: str
    model: str
    timeout_seconds: float
    reachability: str = "not_checked"
    latency_ms: float | None = None
