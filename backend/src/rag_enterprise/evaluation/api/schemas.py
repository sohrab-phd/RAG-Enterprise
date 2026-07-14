"""Evaluation read-adapter HTTP schemas (thin Feature 007 façade)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvaluationRunSummaryDTO(BaseModel):
    """List-row preview for an offline evaluation run."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    name: str
    status: str
    knowledge_base_id: str
    dataset_id: str
    dataset_version: str
    created_at: str | None = None
    top_k: int
    prompt_version: str
    llm: str
    failing_metrics: list[str] = Field(default_factory=list)
    question_count: int
    error_count: int
    recall_at_k: float | None = None
    mrr: float | None = None
    groundedness: float | None = None
    citation_accuracy: float | None = None
    citation_precision_mean: float | None = None
    abstention_precision: float | None = None
    retrieval_latency_mean_ms: float | None = None
    e2e_p95_ms: float | None = None
    e2e_p50_ms: float | None = None
    e2e_mean_ms: float | None = None


class EvaluationRunListDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[EvaluationRunSummaryDTO]


class EvaluationRunDetailDTO(BaseModel):
    """Full run payload: config snapshot + summary + metrics.json."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    config: dict[str, Any]
    summary: dict[str, Any]
    metrics: dict[str, Any]


class EvaluationDatasetListDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[str]
