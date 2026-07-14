"""Evaluation domain models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionLanguage(StrEnum):
    FA = "fa"
    EN = "en"


class EvaluationStatus(StrEnum):
    DEFINED = "defined"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ARCHIVED = "archived"


class CitationRef(BaseModel):
    """Expected citation reference in a golden dataset row."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    document_id: str | None = None
    document_version_id: str | None = None
    rank_hint: int | None = None


class DatasetQuestion(BaseModel):
    """One golden-dataset question record."""

    model_config = ConfigDict(frozen=True)

    id: str
    question: str
    expected_answer: str
    expected_citations: list[CitationRef]
    knowledge_base_id: str
    difficulty: Difficulty
    language: QuestionLanguage
    tags: list[str]
    expect_abstention: bool = False
    notes: str | None = None

    @field_validator("id", "question")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty")
        return value

    @field_validator("tags")
    @classmethod
    def _tags_required(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("tags must contain at least one entry")
        return value


class DatasetManifest(BaseModel):
    """Dataset version manifest."""

    model_config = ConfigDict(frozen=True)

    dataset_id: str
    dataset_version: str
    knowledge_base_id: str
    question_count: int | None = None
    languages: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    notes: str | None = None
    language_default: str | None = None


class GoldenDataset(BaseModel):
    """Loaded golden dataset."""

    model_config = ConfigDict(frozen=True)

    manifest: DatasetManifest
    questions: list[DatasetQuestion]


class ExperimentThresholds(BaseModel):
    """Pass/fail gates for an experiment."""

    model_config = ConfigDict(frozen=True)

    recall_at_k: float | None = 0.70
    mrr: float | None = 0.50
    groundedness: float | None = 0.70
    citation_precision_mean: float | None = 0.70
    abstention_precision: float | None = 0.80


class ExperimentConfig(BaseModel):
    """Immutable experiment configuration snapshot."""

    model_config = ConfigDict(frozen=True)

    experiment_id: str
    name: str
    organization_id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    dataset_id: str
    dataset_version: str
    dataset_path: str
    embedding_model: str = "BAAI/bge-m3"
    chunk_size: int = 1000
    overlap: int = 125
    top_k: int = 8
    prompt_version: str = "v1"
    llm: str = "gpt-4o-mini"
    min_evidence_score: float = 0.25
    max_history_messages: int = 0
    include_abstain_in_retrieval: bool = False
    max_question_error_rate: float = 0.10
    thresholds: ExperimentThresholds = Field(default_factory=ExperimentThresholds)
    permissions: frozenset[str] = frozenset(
        {
            "knowledge_base:read",
            "document:read",
            "organization:evaluation:manage",
        }
    )
    created_at: datetime | None = None
    created_by_user_id: uuid.UUID | None = None


class QuestionOutcome(BaseModel):
    """Per-question evaluation outcome."""

    model_config = ConfigDict(frozen=True)

    question_id: str
    status: str
    expect_abstention: bool = False
    expected_chunk_ids: list[str] = Field(default_factory=list)
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    cited_chunk_ids: list[str] = Field(default_factory=list)
    generation_status: str | None = None
    answer: str | None = None
    abstained: bool = False
    retrieval_latency_ms: int | None = None
    generation_latency_ms: int | None = None
    e2e_latency_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    error_code: str | None = None
    warnings: list[str] = Field(default_factory=list)


class RetrievalMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    recall_at_k: float | None
    mrr: float | None
    k: int
    n: int


class GenerationMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    groundedness: float | None
    citation_precision_mean: float | None
    citation_accuracy: float | None
    abstention_precision: float | None
    abstention_recall: float | None
    n_answerable: int
    n_abstain_cases: int


class LatencyMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    e2e_p50: float | None
    e2e_p95: float | None
    e2e_mean: float | None
    retrieval_mean: float | None = None
    generation_mean: float | None = None


class TokenMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_mean: float | None
    missing_count: int


class MetricsReport(BaseModel):
    """Aggregate metrics for an experiment."""

    model_config = ConfigDict(frozen=True)

    dataset_id: str
    dataset_version: str
    experiment_id: str
    retrieval: RetrievalMetrics
    generation: GenerationMetrics
    latency_ms: LatencyMetrics
    tokens: TokenMetrics
    by_language: dict[str, dict[str, Any]] = Field(default_factory=dict)


class EvaluationSummary(BaseModel):
    """Final experiment summary."""

    model_config = ConfigDict(frozen=True)

    experiment_id: str
    status: EvaluationStatus
    metrics: MetricsReport
    failing_metrics: list[str] = Field(default_factory=list)
    question_count: int
    error_count: int
    artifact_dir: str
