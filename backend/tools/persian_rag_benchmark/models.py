"""Diagnostic domain models for the Persian RAG benchmark."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class FailureLabel(StrEnum):
    DOCUMENT_EXTRACTION = "DOCUMENT_EXTRACTION"
    TEXT_NORMALIZATION = "TEXT_NORMALIZATION"
    UNICODE_NORMALIZATION = "UNICODE_NORMALIZATION"
    HALFSPACE_NORMALIZATION = "HALFSPACE_NORMALIZATION"
    LANGUAGE_DETECTION = "LANGUAGE_DETECTION"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    INDEXING = "INDEXING"
    RETRIEVAL = "RETRIEVAL"
    LOW_RETRIEVAL_SCORE = "LOW_RETRIEVAL_SCORE"
    WRONG_DOCUMENT = "WRONG_DOCUMENT"
    WRONG_CHUNK = "WRONG_CHUNK"
    PROMPT_BUILDER = "PROMPT_BUILDER"
    GENERATION = "GENERATION"
    CITATION = "CITATION"
    EVALUATION = "EVALUATION"
    UNKNOWN = "UNKNOWN"


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

    def to_dataset_row(self) -> dict[str, Any]:
        """Feature-007 compatible dataset.jsonl row."""
        return {
            "id": self.id,
            "question": self.question,
            "expected_answer": self.gold_answer,
            "expected_citations": [
                {
                    "chunk_id": self.expected_chunk_id,
                    "document_id": self.expected_document_id,
                }
            ]
            if self.expected_chunk_id and not self.expect_abstention
            else [],
            "knowledge_base_id": self.knowledge_base_id,
            "difficulty": self.difficulty.value,
            "language": self.language,
            "tags": self.tags or [self.category.value, "fa"],
            "expect_abstention": self.expect_abstention,
            "notes": self.notes,
            # Extended Persian benchmark fields (ignored by Feature 007 loader)
            "category": self.category.value,
            "keywords": self.keywords,
            "supporting_passage": self.supporting_passage,
            "expected_citation_text": self.expected_citation_text,
            "parent_question_id": self.parent_question_id,
            "robustness_kind": self.robustness_kind.value,
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


class QuestionRunResult(BaseModel):
    """Full pipeline capture for one question/variant."""

    model_config = ConfigDict(frozen=True)

    question_id: str
    question: str
    normalized_question: str
    category: str
    difficulty: str
    robustness_kind: str
    parent_question_id: str | None = None
    gold_answer: str
    expected_chunk_id: str
    expected_document_id: str
    retrieved: list[RetrievedEvidence] = Field(default_factory=list)
    retrieval_hit: bool = False
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
    generation_scores: dict[str, float | bool | None] = Field(default_factory=dict)
    failure_labels: list[FailureLabel] = Field(default_factory=list)
    failure_explanation: str | None = None
    passed: bool = False
    warnings: list[str] = Field(default_factory=list)


class SubsystemScore(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    score: float
    details: dict[str, Any] = Field(default_factory=dict)


class AcceptanceReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str = "1.0.0"
    production_ready_for_persian: bool
    overall_score: float
    subsystem_scores: list[SubsystemScore]
    major_weaknesses: list[str]
    top_failing_questions: list[dict[str, Any]]
    top_failure_causes: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    notes: str | None = None


class BenchmarkReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    run_name: str
    created_at: str
    config: dict[str, Any]
    overall_health_score: float
    pipeline_health: dict[str, Any]
    persian_language_health: dict[str, Any]
    retrieval_health: dict[str, Any]
    generation_health: dict[str, Any]
    citation_health: dict[str, Any]
    chunk_health: dict[str, Any]
    embedding_health: dict[str, Any]
    failure_categories: dict[str, int]
    per_document: list[dict[str, Any]]
    questions: list[QuestionRunResult]
    acceptance: AcceptanceReport
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
