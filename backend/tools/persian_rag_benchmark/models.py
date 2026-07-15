"""Diagnostic domain models for the Persian RAG benchmark."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tools.persian_rag_benchmark.trust import EvaluationCohort, GoldProvenance, MetricTrust


class QuestionCategory(StrEnum):
    FACTUAL = "factual"
    POLICY_LOOKUP = "policy_lookup"
    NUMERICAL = "numerical"
    DATE = "date"
    DEFINITION = "definition"
    PROCEDURE = "procedure"
    EXCEPTION = "exception"
    COMPARISON = "comparison"
    YES_NO = "yes_no"
    LIST = "list"
    RESPONSIBILITY = "responsibility"
    PERMISSION = "permission"
    RESTRICTION = "restriction"
    DEADLINE = "deadline"
    MULTI_STEP = "multi_step"
    MULTI_HOP = "multi_hop"
    CROSS_SECTION = "cross_section"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class RobustnessKind(StrEnum):
    NORMAL = "normal"
    PARAPHRASE = "paraphrase"
    FORMAL = "formal"
    INFORMAL = "informal"
    SYNONYM = "synonym"
    ARABIC_YEH_KAF = "arabic_yeh_kaf"
    HALFSPACE = "halfspace"
    DIGIT_LATIN = "digit_latin"
    DIGIT_PERSIAN = "digit_persian"
    DIGIT_ARABIC_INDIC = "digit_arabic_indic"
    PUNCTUATION = "punctuation"
    NO_PUNCTUATION = "no_punctuation"
    WHITESPACE = "whitespace"
    SPELLING = "spelling"


class ChunkSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    sequence_number: int
    text: str
    language: str | None = None
    heading: str | None = None
    start_offset: int = 0
    end_offset: int = 0
    document_title: str | None = None


class GroundTruthQuestion(BaseModel):
    """Extended golden question used by this benchmark (JSONL-serializable)."""

    model_config = ConfigDict(frozen=True)

    id: str
    question: str
    gold_answer: str
    supporting_passage: str
    expected_citation_text: str
    expected_document_id: str
    expected_chunk_id: str
    knowledge_base_id: str
    category: QuestionCategory
    difficulty: Difficulty
    keywords: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    language: str = "fa"
    expect_abstention: bool = False
    notes: str | None = None
    parent_question_id: str | None = None
    robustness_kind: RobustnessKind = RobustnessKind.NORMAL
    gold_provenance: GoldProvenance = GoldProvenance.CURATED_EXTERNAL
    eligible_for_measured_retrieval: bool = True

    def to_dataset_row(self) -> dict[str, Any]:
        """Feature-007 compatible dataset.jsonl row + benchmark extensions."""
        return {
            "id": self.id,
            "question": self.question,
            "expected_answer": self.gold_answer,
            "expected_citations": (
                [
                    {
                        "chunk_id": self.expected_chunk_id,
                        "document_id": self.expected_document_id,
                    }
                ]
                if self.expected_chunk_id and not self.expect_abstention
                else []
            ),
            "knowledge_base_id": self.knowledge_base_id,
            "difficulty": self.difficulty.value,
            "language": self.language,
            "tags": self.tags or [self.category.value, "fa"],
            "expect_abstention": self.expect_abstention,
            "notes": self.notes,
            "category": self.category.value,
            "keywords": self.keywords,
            "supporting_passage": self.supporting_passage,
            "expected_citation_text": self.expected_citation_text,
            "parent_question_id": self.parent_question_id,
            "robustness_kind": self.robustness_kind.value,
            "gold_provenance": self.gold_provenance.value,
            "eligible_for_measured_retrieval": self.eligible_for_measured_retrieval,
        }


class RetrievedEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    document_id: str
    document_version_id: str
    score: float
    rank: int
    text: str
    language: str | None = None


class RcaFinding(BaseModel):
    """Non-deterministic RCA hypothesis with confidence and evidence."""

    model_config = ConfigDict(frozen=True)

    likely_root_cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)


class QuestionRunResult(BaseModel):
    """Full pipeline capture for one question/variant."""

    model_config = ConfigDict(frozen=True)

    question_id: str
    question: str
    normalized_question: str
    category: str
    difficulty: str
    robustness_kind: str
    cohort: EvaluationCohort
    gold_provenance: GoldProvenance
    eligible_for_measured_retrieval: bool
    parent_question_id: str | None = None
    gold_answer: str
    expected_chunk_id: str
    expected_document_id: str
    retrieved: list[RetrievedEvidence] = Field(default_factory=list)
    hit_at_k: float | None = None
    recall_at_k: float | None = None
    precision_at_k: float | None = None
    mrr: float | None = None
    retrieval_rank: int | None = None
    correct_document: bool = False
    correct_chunk: bool = False
    avg_retrieval_score: float | None = None
    detected_language: str | None = None
    prompt_preview: str | None = None
    generated_answer: str | None = None
    citations: list[str] = Field(default_factory=list)
    generation_status: str | None = None
    abstained: bool = False
    retrieval_latency_ms: int | None = None
    generation_latency_ms: int | None = None
    e2e_latency_ms: int | None = None
    language_issues: list[str] = Field(default_factory=list)
    # Heuristic / derived generation diagnostics (explicit names)
    exact_match: bool | None = None
    lexical_overlap: float | None = None
    heuristic_fluency_estimate: float | None = None
    entity_match_estimate: float | None = None
    procedure_match_estimate: float | None = None
    groundedness_estimate: bool | None = None
    hallucination_risk_estimate: bool | None = None
    citation_accuracy: bool | None = None
    numeric_accuracy: float | None = None
    context_diagnostics: dict[str, object] = Field(default_factory=dict)
    rca: list[RcaFinding] = Field(default_factory=list)
    passed_measured: bool = False
    warnings: list[str] = Field(default_factory=list)


class TrustMetricRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric: str
    trust: MetricTrust
    definition: str
    baseline_value: float | int | str | None = None
    robustness_value: float | int | str | None = None


class SubsystemScore(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    cohort: EvaluationCohort
    score: float | None
    trust: MetricTrust
    computation: str
    details: dict[str, Any] = Field(default_factory=dict)


class BenchmarkReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    run_name: str
    created_at: str
    config: dict[str, Any]
    trust_report: list[TrustMetricRow]
    baseline_metrics: dict[str, Any]
    robustness_metrics: dict[str, Any]
    subsystem_scores: list[SubsystemScore]
    persian_language_health: dict[str, Any]
    chunk_health: dict[str, Any]
    embedding_health: dict[str, Any]
    retrieval_detail: dict[str, Any] = Field(default_factory=dict)
    context_assembly: dict[str, Any] = Field(default_factory=dict)
    per_document: list[dict[str, Any]]
    questions: list[QuestionRunResult]
    notes: list[str] = Field(default_factory=list)
