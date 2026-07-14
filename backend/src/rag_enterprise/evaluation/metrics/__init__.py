"""Deterministic evaluation metrics (no LLM judging)."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from statistics import mean

from rag_enterprise.evaluation.models import (
    DatasetQuestion,
    GenerationMetrics,
    LatencyMetrics,
    MetricsReport,
    QuestionOutcome,
    RetrievalMetrics,
    TokenMetrics,
)


def recall_at_k(
    outcomes: Sequence[QuestionOutcome],
    *,
    include_abstain: bool = False,
) -> tuple[float | None, int]:
    """Recall@K: fraction of questions with ≥1 expected chunk in retrieved top-K."""
    eligible = _retrieval_eligible(outcomes, include_abstain=include_abstain)
    if not eligible:
        return None, 0
    hits = 0
    for outcome in eligible:
        expected = set(outcome.expected_chunk_ids)
        retrieved = set(outcome.retrieved_chunk_ids)
        if expected & retrieved:
            hits += 1
    return hits / len(eligible), len(eligible)


def mean_reciprocal_rank(
    outcomes: Sequence[QuestionOutcome],
    *,
    include_abstain: bool = False,
) -> tuple[float | None, int]:
    """MRR over questions (0 when no expected chunk appears)."""
    eligible = _retrieval_eligible(outcomes, include_abstain=include_abstain)
    if not eligible:
        return None, 0
    scores: list[float] = []
    for outcome in eligible:
        expected = set(outcome.expected_chunk_ids)
        rr = 0.0
        for rank, chunk_id in enumerate(outcome.retrieved_chunk_ids, start=1):
            if chunk_id in expected:
                rr = 1.0 / rank
                break
        scores.append(rr)
    return mean(scores), len(eligible)


def citation_precision(cited: Sequence[str], expected: Sequence[str]) -> float | None:
    """|cited ∩ expected| / |cited|; None when cited is empty."""
    if not cited:
        return None
    expected_set = set(expected)
    return len(set(cited) & expected_set) / len(set(cited))


def citation_recall(cited: Sequence[str], expected: Sequence[str]) -> float | None:
    """|cited ∩ expected| / |expected|; None when expected is empty."""
    if not expected:
        return None
    return len(set(cited) & set(expected)) / len(set(expected))


def is_citation_accurate(cited: Sequence[str], expected: Sequence[str]) -> bool | None:
    """True when precision and recall are both 1.0; None if expected empty."""
    if not expected:
        return None
    precision = citation_precision(cited, expected)
    recall = citation_recall(cited, expected)
    if precision is None or recall is None:
        return False
    return precision >= 1.0 and recall >= 1.0


def is_grounded(
    *,
    generation_status: str | None,
    cited_chunk_ids: Sequence[str],
    expected_chunk_ids: Sequence[str],
    retrieved_chunk_ids: Sequence[str],
) -> bool:
    """Citation-based groundedness for a completed answer."""
    if generation_status != "completed":
        return False
    retrieved = set(retrieved_chunk_ids)
    cited = set(cited_chunk_ids)
    expected = set(expected_chunk_ids)
    if cited and not cited.issubset(retrieved):
        return False
    return bool((cited & expected) or (cited & retrieved))


def abstention_precision(outcomes: Sequence[QuestionOutcome]) -> tuple[float | None, int]:
    """Among abstentions, fraction where abstention was expected."""
    abstained = [o for o in outcomes if o.abstained or o.generation_status == "abstained"]
    if not abstained:
        return None, 0
    correct = sum(1 for o in abstained if o.expect_abstention)
    return correct / len(abstained), len(abstained)


def abstention_recall(outcomes: Sequence[QuestionOutcome]) -> tuple[float | None, int]:
    """Among expect_abstention questions, fraction that abstained."""
    expected = [o for o in outcomes if o.expect_abstention]
    if not expected:
        return None, 0
    hit = sum(1 for o in expected if o.abstained or o.generation_status == "abstained")
    return hit / len(expected), len(expected)


def percentile(values: Sequence[float], p: float) -> float | None:
    """Nearest-rank percentile for a sorted copy of values."""
    if not values:
        return None
    if p <= 0:
        return float(min(values))
    if p >= 100:
        return float(max(values))
    ordered = sorted(values)
    rank = math.ceil((p / 100.0) * len(ordered)) - 1
    rank = max(0, min(rank, len(ordered) - 1))
    return float(ordered[rank])


def language_breakdown(
    outcomes: Sequence[QuestionOutcome],
    questions: Sequence[DatasetQuestion],
) -> dict[str, dict[str, int]]:
    """Per-language diagnostic counts for metrics report."""
    language_by_id = {q.id: q.language.value for q in questions}
    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"n": 0, "ok": 0, "error": 0, "abstained": 0}
    )
    for outcome in outcomes:
        language = language_by_id.get(outcome.question_id, "unknown")
        bucket = counts[language]
        bucket["n"] += 1
        if outcome.status == "ok":
            bucket["ok"] += 1
        else:
            bucket["error"] += 1
        if outcome.abstained or outcome.generation_status == "abstained":
            bucket["abstained"] += 1
    return dict(counts)


def aggregate_metrics(
    *,
    outcomes: Sequence[QuestionOutcome],
    dataset_id: str,
    dataset_version: str,
    experiment_id: str,
    top_k: int,
    include_abstain_in_retrieval: bool = False,
    questions: Sequence[DatasetQuestion] | None = None,
) -> MetricsReport:
    """Build the aggregate metrics report from per-question outcomes."""
    ok_outcomes = [o for o in outcomes if o.status == "ok"]

    recall, n_retrieval = recall_at_k(ok_outcomes, include_abstain=include_abstain_in_retrieval)
    mrr, _ = mean_reciprocal_rank(ok_outcomes, include_abstain=include_abstain_in_retrieval)

    answerable_completed = [
        o for o in ok_outcomes if not o.expect_abstention and o.generation_status == "completed"
    ]
    grounded_count = 0
    precision_scores: list[float] = []
    accuracy_flags: list[bool] = []
    for outcome in answerable_completed:
        if not outcome.expected_chunk_ids:
            continue
        if is_grounded(
            generation_status=outcome.generation_status,
            cited_chunk_ids=outcome.cited_chunk_ids,
            expected_chunk_ids=outcome.expected_chunk_ids,
            retrieved_chunk_ids=outcome.retrieved_chunk_ids,
        ):
            grounded_count += 1
        precision = citation_precision(outcome.cited_chunk_ids, outcome.expected_chunk_ids)
        if precision is not None:
            precision_scores.append(precision)
        accurate = is_citation_accurate(outcome.cited_chunk_ids, outcome.expected_chunk_ids)
        if accurate is not None:
            accuracy_flags.append(accurate)

    n_answerable_denom = sum(1 for o in ok_outcomes if not o.expect_abstention)
    groundedness = grounded_count / n_answerable_denom if n_answerable_denom > 0 else None
    citation_precision_mean = mean(precision_scores) if precision_scores else None
    citation_accuracy = (
        sum(1 for flag in accuracy_flags if flag) / len(accuracy_flags) if accuracy_flags else None
    )

    abstain_cases = [o for o in ok_outcomes if o.expect_abstention]
    abs_prec, _ = abstention_precision(ok_outcomes)
    abs_rec, _ = abstention_recall(ok_outcomes)

    e2e = [float(o.e2e_latency_ms) for o in ok_outcomes if o.e2e_latency_ms is not None]
    retrieval_lat = [
        float(o.retrieval_latency_ms) for o in ok_outcomes if o.retrieval_latency_ms is not None
    ]
    generation_lat = [
        float(o.generation_latency_ms) for o in ok_outcomes if o.generation_latency_ms is not None
    ]

    token_totals = [float(o.total_tokens) for o in ok_outcomes if o.total_tokens is not None]
    missing_tokens = sum(1 for o in ok_outcomes if o.total_tokens is None)

    by_language: dict[str, dict[str, int]] = {}
    if questions is not None:
        by_language = language_breakdown(outcomes, questions)

    return MetricsReport(
        dataset_id=dataset_id,
        dataset_version=dataset_version,
        experiment_id=experiment_id,
        retrieval=RetrievalMetrics(
            recall_at_k=recall,
            mrr=mrr,
            k=top_k,
            n=n_retrieval,
        ),
        generation=GenerationMetrics(
            groundedness=groundedness,
            citation_precision_mean=citation_precision_mean,
            citation_accuracy=citation_accuracy,
            abstention_precision=abs_prec,
            abstention_recall=abs_rec,
            n_answerable=n_answerable_denom,
            n_abstain_cases=len(abstain_cases),
        ),
        latency_ms=LatencyMetrics(
            e2e_p50=percentile(e2e, 50),
            e2e_p95=percentile(e2e, 95),
            e2e_mean=mean(e2e) if e2e else None,
            retrieval_mean=mean(retrieval_lat) if retrieval_lat else None,
            generation_mean=mean(generation_lat) if generation_lat else None,
        ),
        tokens=TokenMetrics(
            total_mean=mean(token_totals) if token_totals else None,
            missing_count=missing_tokens,
        ),
        by_language=by_language,
    )


def evaluate_thresholds(
    report: MetricsReport,
    *,
    recall_at_k: float | None = None,
    mrr: float | None = None,
    groundedness: float | None = None,
    citation_precision_mean: float | None = None,
    abstention_precision: float | None = None,
) -> list[str]:
    """Return names of metrics that fail configured thresholds."""
    failing: list[str] = []
    checks: list[tuple[str, float | None, float | None]] = [
        ("recall_at_k", report.retrieval.recall_at_k, recall_at_k),
        ("mrr", report.retrieval.mrr, mrr),
        ("groundedness", report.generation.groundedness, groundedness),
        (
            "citation_precision_mean",
            report.generation.citation_precision_mean,
            citation_precision_mean,
        ),
        (
            "abstention_precision",
            report.generation.abstention_precision,
            abstention_precision,
        ),
    ]
    for name, actual, threshold in checks:
        if threshold is None or actual is None:
            continue
        if actual < threshold:
            failing.append(name)
    return failing


def _retrieval_eligible(
    outcomes: Sequence[QuestionOutcome],
    *,
    include_abstain: bool,
) -> list[QuestionOutcome]:
    if include_abstain:
        return [o for o in outcomes if o.expected_chunk_ids]
    return [o for o in outcomes if not o.expect_abstention and o.expected_chunk_ids]
