"""Experiment runner: retrieve → generate → score → persist."""

from __future__ import annotations

import logging
import time
from typing import Protocol

from rag_enterprise.evaluation.dataset import load_dataset
from rag_enterprise.evaluation.exceptions import (
    DatasetValidationError,
    KnowledgeBaseUnavailableError,
)
from rag_enterprise.evaluation.metrics import aggregate_metrics, evaluate_thresholds
from rag_enterprise.evaluation.models import (
    DatasetQuestion,
    EvaluationStatus,
    EvaluationSummary,
    ExperimentConfig,
    QuestionOutcome,
)
from rag_enterprise.evaluation.storage import ExperimentStorage
from rag_enterprise.generation.models import GenerationRequest, GenerationResult
from rag_enterprise.retrieval.exceptions import RetrievalError
from rag_enterprise.retrieval.models import SearchRequest, SearchResponse

logger = logging.getLogger(__name__)


class RetrievalCaller(Protocol):
    async def retrieve(self, request: SearchRequest) -> SearchResponse:
        """Run retrieval for one question."""


class GenerationCaller(Protocol):
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Run generation for one question."""


class ExperimentRunner:
    """Execute a pinned experiment against retrieval and generation black boxes."""

    def __init__(
        self,
        *,
        retrieval_service: RetrievalCaller,
        generation_service: GenerationCaller,
        storage: ExperimentStorage,
    ) -> None:
        self._retrieval = retrieval_service
        self._generation = generation_service
        self._storage = storage

    async def run(self, config: ExperimentConfig) -> EvaluationSummary:
        """Run all dataset questions and persist artifacts under experiments/."""
        self._storage.write_config(config)
        dataset = load_dataset(config.dataset_path)

        if dataset.manifest.dataset_id != config.dataset_id:
            raise DatasetValidationError(
                "dataset_id mismatch",
                details={
                    "config": config.dataset_id,
                    "manifest": dataset.manifest.dataset_id,
                },
            )
        if dataset.manifest.dataset_version != config.dataset_version:
            raise DatasetValidationError(
                "dataset_version mismatch",
                details={
                    "config": config.dataset_version,
                    "manifest": dataset.manifest.dataset_version,
                },
            )

        outcomes: list[QuestionOutcome] = []
        for question in dataset.questions:
            outcome = await self._run_question(config, question)
            outcomes.append(outcome)

        error_count = sum(1 for o in outcomes if o.status != "ok")
        error_rate = error_count / len(outcomes) if outcomes else 1.0
        report = aggregate_metrics(
            outcomes=outcomes,
            dataset_id=config.dataset_id,
            dataset_version=config.dataset_version,
            experiment_id=config.experiment_id,
            top_k=config.top_k,
            include_abstain_in_retrieval=config.include_abstain_in_retrieval,
            questions=dataset.questions,
        )

        failing = evaluate_thresholds(
            report,
            recall_at_k=config.thresholds.recall_at_k,
            mrr=config.thresholds.mrr,
            groundedness=config.thresholds.groundedness,
            citation_precision_mean=config.thresholds.citation_precision_mean,
            abstention_precision=config.thresholds.abstention_precision,
        )
        if error_rate > config.max_question_error_rate:
            failing = ["aggregate_incomplete", *failing]

        status = EvaluationStatus.PASSED if not failing else EvaluationStatus.FAILED
        artifact_dir = str(self._storage.experiment_dir(config.experiment_id))
        summary = EvaluationSummary(
            experiment_id=config.experiment_id,
            status=status,
            metrics=report,
            failing_metrics=failing,
            question_count=len(outcomes),
            error_count=error_count,
            artifact_dir=artifact_dir,
        )
        self._storage.write_results(config.experiment_id, outcomes)
        self._storage.write_metrics(config.experiment_id, report)
        self._storage.write_summary(summary)
        logger.info(
            "evaluation_completed",
            extra={
                "experiment_id": config.experiment_id,
                "status": status.value,
                "question_count": len(outcomes),
                "error_count": error_count,
            },
        )
        return summary

    async def _run_question(
        self,
        config: ExperimentConfig,
        question: DatasetQuestion,
    ) -> QuestionOutcome:
        expected_ids = [c.chunk_id for c in question.expected_citations]
        e2e_started = time.perf_counter()
        retrieved_ids: list[str] = []
        retrieval_ms: int | None = None
        generation_ms: int | None = None
        warnings: list[str] = []

        if not question.expect_abstention and not expected_ids:
            warnings.append("empty_expected_citations_skipped_from_citation_metrics")

        try:
            retrieval_started = time.perf_counter()
            search = await self._retrieval.retrieve(
                SearchRequest(
                    query_text=question.question,
                    organization_id=config.organization_id,
                    workspace_id=config.workspace_id,
                    knowledge_base_id=config.knowledge_base_id,
                    top_k=config.top_k,
                    language=question.language.value,
                    user_id=config.user_id,
                    permissions=config.permissions,
                )
            )
            retrieval_ms = int((time.perf_counter() - retrieval_started) * 1000)
            retrieved_ids = [str(chunk.chunk_id) for chunk in search.results]
            warnings.extend(search.warnings)
        except RetrievalError as exc:
            if exc.code in {
                "knowledge_base_unavailable",
                "knowledge_base_not_found",
            }:
                raise KnowledgeBaseUnavailableError(details={"error": exc.code}) from exc
            e2e_ms = int((time.perf_counter() - e2e_started) * 1000)
            return QuestionOutcome(
                question_id=question.id,
                status="error",
                expect_abstention=question.expect_abstention,
                expected_chunk_ids=expected_ids,
                retrieval_latency_ms=retrieval_ms,
                e2e_latency_ms=e2e_ms,
                error_code=exc.code,
                warnings=warnings,
            )

        try:
            generation_started = time.perf_counter()
            generation = await self._generation.generate(
                GenerationRequest(
                    question=question.question,
                    organization_id=config.organization_id,
                    workspace_id=config.workspace_id,
                    knowledge_base_id=config.knowledge_base_id,
                    user_id=config.user_id,
                    permissions=config.permissions,
                    history=[],
                    language_hint=question.language.value,
                    top_k=config.top_k,
                )
            )
            generation_ms = int((time.perf_counter() - generation_started) * 1000)
        except Exception as exc:
            e2e_ms = int((time.perf_counter() - e2e_started) * 1000)
            code = getattr(exc, "code", "question_error")
            return QuestionOutcome(
                question_id=question.id,
                status="error",
                expect_abstention=question.expect_abstention,
                expected_chunk_ids=expected_ids,
                retrieved_chunk_ids=retrieved_ids,
                retrieval_latency_ms=retrieval_ms,
                generation_latency_ms=generation_ms,
                e2e_latency_ms=e2e_ms,
                error_code=str(code),
                warnings=warnings,
            )

        cited_ids = [str(c.chunk_id) for c in generation.citations]
        e2e_ms = int((time.perf_counter() - e2e_started) * 1000)
        abstained = generation.status.value == "abstained"
        return QuestionOutcome(
            question_id=question.id,
            status="ok",
            expect_abstention=question.expect_abstention,
            expected_chunk_ids=expected_ids,
            retrieved_chunk_ids=retrieved_ids,
            cited_chunk_ids=cited_ids,
            generation_status=generation.status.value,
            answer=generation.answer,
            abstained=abstained,
            retrieval_latency_ms=retrieval_ms,
            generation_latency_ms=generation_ms,
            e2e_latency_ms=e2e_ms,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            error_code=None,
            warnings=warnings + list(generation.warnings),
        )
