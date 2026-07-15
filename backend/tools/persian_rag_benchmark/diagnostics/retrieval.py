"""Retrieval quality diagnostics with cohort isolation."""

from __future__ import annotations

from typing import Any

from tools.persian_rag_benchmark.ir_metrics import aggregate_ir
from tools.persian_rag_benchmark.models import QuestionRunResult
from tools.persian_rag_benchmark.trust import EvaluationCohort, MetricTrust


def evaluate_retrieval_by_cohort(
    results: list[QuestionRunResult],
    *,
    top_k: int,
) -> dict[str, Any]:
    """Compute IR metrics separately for baseline and robustness cohorts.

    Measured retrieval metrics include only questions with
    ``eligible_for_measured_retrieval`` (curated external gold).
    """
    latencies = [
        item.retrieval_latency_ms for item in results if item.retrieval_latency_ms is not None
    ]
    scores = [
        score
        for item in results
        if item.eligible_for_measured_retrieval
        for score in (hit.score for hit in item.retrieved)
    ]
    return {
        EvaluationCohort.BASELINE.value: _eval_cohort(
            [
                item
                for item in results
                if item.cohort == EvaluationCohort.BASELINE and item.eligible_for_measured_retrieval
            ],
            top_k=top_k,
            cohort=EvaluationCohort.BASELINE,
        ),
        EvaluationCohort.ROBUSTNESS.value: _eval_cohort(
            [
                item
                for item in results
                if item.cohort == EvaluationCohort.ROBUSTNESS
                and item.eligible_for_measured_retrieval
            ],
            top_k=top_k,
            cohort=EvaluationCohort.ROBUSTNESS,
        ),
        "excluded_auto_corpus_probe_count": sum(
            1 for item in results if not item.eligible_for_measured_retrieval
        ),
        "avg_retrieval_latency_ms": (sum(latencies) / len(latencies) if latencies else None),
        "score_histogram_all_measured": _simple_histogram(scores),
        "definitions": {
            "hit_at_k": MetricTrust.MEASURED.value,
            "recall_at_k": MetricTrust.MEASURED.value,
            "precision_at_k": MetricTrust.MEASURED.value,
            "mrr": MetricTrust.MEASURED.value,
        },
    }


def _simple_histogram(scores: list[float], *, bin_width: float = 0.05) -> dict[str, int]:
    from collections import Counter

    counts: Counter[str] = Counter()
    for score in scores:
        start = int(score / bin_width) * bin_width
        end = start + bin_width
        counts[f"{start:.2f}-{end:.2f}"] += 1
    return dict(sorted(counts.items()))


def _eval_cohort(
    results: list[QuestionRunResult],
    *,
    top_k: int,
    cohort: EvaluationCohort,
) -> dict[str, Any]:
    rows: list[dict[str, float]] = []
    for item in results:
        if item.hit_at_k is None:
            continue
        rows.append(
            {
                "hit_at_k": float(item.hit_at_k),
                "recall_at_k": float(item.recall_at_k or 0.0),
                "precision_at_k": float(item.precision_at_k or 0.0),
                "mrr": float(item.mrr or 0.0),
            }
        )
    aggregated = aggregate_ir(rows)
    scores = [item.avg_retrieval_score for item in results if item.avg_retrieval_score is not None]
    successes = sum(1 for item in results if (item.hit_at_k or 0.0) >= 1.0)
    failures = sum(1 for item in results if item.hit_at_k is not None and item.hit_at_k < 1.0)
    return {
        "cohort": cohort.value,
        "top_k": top_k,
        "trust": MetricTrust.MEASURED.value,
        **aggregated,
        "avg_retrieval_score": (sum(scores) / len(scores) if scores else None),
        "successful_queries": successes,
        "failed_queries": failures,
        "correct_document_rate": (
            sum(1 for item in results if item.correct_document) / len(results) if results else None
        ),
        "correct_chunk_rate": (
            sum(1 for item in results if item.correct_chunk) / len(results) if results else None
        ),
    }


def explain_retrieval_miss(result: QuestionRunResult) -> list[str]:
    evidence: list[str] = []
    if result.hit_at_k == 1.0:
        return evidence
    if not result.retrieved:
        evidence.append("RetrievalService returned zero chunks.")
        return evidence
    if result.correct_document and not result.correct_chunk:
        evidence.append(
            f"Expected document {result.expected_document_id} appeared but "
            f"expected chunk {result.expected_chunk_id} did not."
        )
    top = result.retrieved[0]
    evidence.append(f"Top-1 chunk={top.chunk_id} score={top.score:.4f} document={top.document_id}.")
    return evidence
