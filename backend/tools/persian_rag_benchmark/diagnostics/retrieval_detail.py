"""Extended dense-retrieval diagnostics (score/rank histograms, false abstains)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from tools.persian_rag_benchmark.ir_metrics import hit_at_k, reciprocal_rank
from tools.persian_rag_benchmark.models import QuestionRunResult

_EVIDENCE_THRESHOLDS: tuple[float, ...] = (0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30)
_TOP_K_CANDIDATES: tuple[int, ...] = (1, 3, 5, 8, 10, 12)


def build_retrieval_detail(
    results: list[QuestionRunResult],
    *,
    configured_top_k: int,
    configured_min_evidence_score: float,
) -> dict[str, Any]:
    """Aggregate retrieval diagnostics for Measured curated questions."""
    eligible = [item for item in results if item.eligible_for_measured_retrieval]
    scored = [item for item in eligible if item.hit_at_k is not None]

    all_scores: list[float] = []
    top1_scores: list[float] = []
    gold_scores: list[float] = []
    gold_ranks: list[int] = []
    latencies: list[int] = []
    success: list[QuestionRunResult] = []
    failed: list[QuestionRunResult] = []

    for item in scored:
        if item.retrieval_latency_ms is not None:
            latencies.append(item.retrieval_latency_ms)
        for hit in item.retrieved:
            all_scores.append(float(hit.score))
        if item.retrieved:
            top1_scores.append(float(item.retrieved[0].score))
        gold = _gold_hit(item)
        if gold is not None:
            gold_scores.append(float(gold.score))
            gold_ranks.append(int(gold.rank))
        if (item.hit_at_k or 0.0) >= 1.0:
            success.append(item)
        else:
            failed.append(item)

    false_abstains = analyze_false_abstains(
        eligible,
        configured_min_evidence_score=configured_min_evidence_score,
    )
    threshold_sweep = sweep_evidence_thresholds(scored)
    top_k_sweep = sweep_top_k(scored, candidates=_TOP_K_CANDIDATES)
    expansion = classify_query_expansion_gaps(failed)

    recommended_threshold = _recommend_threshold(threshold_sweep)
    recommended_top_k = _recommend_top_k(top_k_sweep, configured_top_k=configured_top_k)

    return {
        "configured_top_k": configured_top_k,
        "configured_min_evidence_score": configured_min_evidence_score,
        "n_measured": len(scored),
        "successful_retrieval": len(success),
        "failed_retrieval": len(failed),
        "success_rate": (len(success) / len(scored) if scored else None),
        "avg_retrieval_latency_ms": (sum(latencies) / len(latencies) if latencies else None),
        "score_distribution": _score_stats(all_scores),
        "top1_score_distribution": _score_stats(top1_scores),
        "gold_chunk_score_distribution": _score_stats(gold_scores),
        "score_histogram": _histogram(all_scores, bin_width=0.05),
        "top_k_rank_histogram": dict(sorted(Counter(gold_ranks).items())),
        "false_abstains": false_abstains,
        "threshold_sweep": threshold_sweep,
        "top_k_sweep": top_k_sweep,
        "query_expansion_diagnostics": expansion,
        "recommended_min_evidence_score": recommended_threshold,
        "recommended_top_k": recommended_top_k,
        "per_question": [_question_row(item) for item in scored],
        "failed_questions": [_question_row(item) for item in failed],
        "false_abstain_questions": false_abstains["cases"],
    }


def analyze_false_abstains(
    results: list[QuestionRunResult],
    *,
    configured_min_evidence_score: float,
) -> dict[str, Any]:
    """Correct chunk retrieved, but generation abstains on evidence score."""
    cases: list[dict[str, Any]] = []
    for item in results:
        if not item.eligible_for_measured_retrieval:
            continue
        if not item.expected_chunk_id or (item.hit_at_k or 0.0) < 1.0:
            continue
        if not item.abstained:
            continue
        max_score = max((hit.score for hit in item.retrieved), default=0.0)
        gold = _gold_hit(item)
        cases.append(
            {
                "question_id": item.question_id,
                "question": item.question,
                "robustness_kind": item.robustness_kind,
                "max_score": max_score,
                "gold_chunk_score": gold.score if gold else None,
                "gold_rank": gold.rank if gold else item.retrieval_rank,
                "generation_status": item.generation_status,
                "configured_min_evidence_score": configured_min_evidence_score,
                "threshold_triggered": max_score < configured_min_evidence_score,
            }
        )
    return {
        "count": len(cases),
        "rate": (len(cases) / len(results) if results else 0.0),
        "cases": cases,
    }


def sweep_evidence_thresholds(
    results: list[QuestionRunResult],
    thresholds: tuple[float, ...] = _EVIDENCE_THRESHOLDS,
) -> list[dict[str, Any]]:
    """Sweep GENERATION_MIN_EVIDENCE_SCORE-style gates on captured retrieval scores."""
    rows: list[dict[str, Any]] = []
    n = len(results) or 1
    for threshold in thresholds:
        hit_values: list[float] = []
        mrr_values: list[float] = []
        false_abstains = 0
        hallucinations = 0
        answers = 0
        for item in results:
            max_score = max((hit.score for hit in item.retrieved), default=0.0)
            would_abstain = max_score < threshold or not item.retrieved
            retrieved_ids = [hit.chunk_id for hit in item.retrieved]
            expected = [item.expected_chunk_id] if item.expected_chunk_id else []
            # Retrieval metrics use raw top-k (unchanged by gate).
            if expected:
                hit_values.append(hit_at_k(retrieved_ids, expected, k=len(retrieved_ids) or 1))
                mrr_values.append(reciprocal_rank(retrieved_ids, expected))
            if expected and (item.hit_at_k or 0.0) >= 1.0 and would_abstain and item.gold_answer:
                false_abstains += 1
            if not would_abstain:
                answers += 1
                if item.hallucination_risk_estimate:
                    hallucinations += 1
        rows.append(
            {
                "min_evidence_score": threshold,
                "hit_at_k": (sum(hit_values) / len(hit_values) if hit_values else None),
                "mrr": (sum(mrr_values) / len(mrr_values) if mrr_values else None),
                "false_abstain_count": false_abstains,
                "false_abstain_rate": false_abstains / n,
                "hallucination_count": hallucinations,
                "hallucination_rate": (hallucinations / answers if answers else 0.0),
                "answer_count": answers,
            }
        )
    return rows


def sweep_top_k(
    results: list[QuestionRunResult],
    *,
    candidates: tuple[int, ...],
) -> list[dict[str, Any]]:
    """Recompute Hit@k / MRR by truncating already-captured ranked lists."""
    rows: list[dict[str, Any]] = []
    for k in candidates:
        hits: list[float] = []
        mrrs: list[float] = []
        for item in results:
            if not item.expected_chunk_id:
                continue
            ids = [hit.chunk_id for hit in item.retrieved[:k]]
            expected = [item.expected_chunk_id]
            hits.append(hit_at_k(ids, expected, k=k))
            mrrs.append(reciprocal_rank(ids, expected))
        rows.append(
            {
                "top_k": k,
                "hit_at_k": (sum(hits) / len(hits) if hits else None),
                "mrr": (sum(mrrs) / len(mrrs) if mrrs else None),
                "n": len(hits),
            }
        )
    return rows


def classify_query_expansion_gaps(failed: list[QuestionRunResult]) -> dict[str, Any]:
    """Attribute retrieval misses to wording-gap classes (diagnostics only; no expansion)."""
    if not failed:
        return {
            "n_failed": 0,
            "note": "No measured retrieval failures to classify.",
            "percentages": {},
            "counts": {},
        }

    counts: Counter[str] = Counter()
    for item in failed:
        labels = _expansion_labels(item)
        for label in labels:
            counts[label] += 1

    total = len(failed)
    percentages = {key: (value / total) * 100.0 for key, value in sorted(counts.items())}
    return {
        "n_failed": total,
        "note": (
            "Percentages are of failed Measured questions; a miss may match "
            "multiple labels. Expansion is NOT implemented — diagnostics only."
        ),
        "counts": dict(counts),
        "percentages": percentages,
    }


def _expansion_labels(item: QuestionRunResult) -> list[str]:
    kind = item.robustness_kind
    labels: list[str] = []
    if kind in {"synonym", "paraphrase", "formal", "informal"}:
        labels.append("synonyms_or_paraphrase")
    if kind in {"spelling"}:
        labels.append("morphology_or_spelling")
    if "اختصار" in item.question or "acronym" in (item.question.lower()):
        labels.append("acronyms")
    if kind in {"paraphrase", "formal", "informal"}:
        labels.append("different_wording")
    # Heuristic word-order / token-set gap vs supporting evidence text.
    if item.retrieved and item.expected_chunk_id:
        gold = _gold_hit(item)
        top = item.retrieved[0]
        q_tokens = set(_tokens(item.normalized_question))
        top_tokens = set(_tokens(top.text))
        gold_tokens = set(_tokens(gold.text)) if gold else set()
        if q_tokens and top_tokens and len(q_tokens & top_tokens) < max(1, len(q_tokens) // 4):
            labels.append("different_wording")
        if gold_tokens and q_tokens:
            q_list = _tokens(item.normalized_question)
            g_list = _tokens(gold.text)
            if set(q_list) == set(g_list) and q_list != g_list:
                labels.append("word_order")
    if kind in {
        "halfspace",
        "arabic_yeh_kaf",
        "digit_latin",
        "digit_persian",
        "digit_arabic_indic",
    }:
        labels.append("surface_normalization")
    if not labels:
        labels.append("unspecified_semantic_gap")
    return sorted(set(labels))


def _recommend_threshold(sweep: list[dict[str, Any]]) -> float:
    """Prefer a safe gate with zero false abstains; default toward 0.25 when possible."""
    if not sweep:
        return 0.25
    zero_fa = [row for row in sweep if float(row["false_abstain_rate"]) <= 0.0]
    pool = zero_fa or sweep
    preferred_order = (0.25, 0.20, 0.15, 0.30, 0.10, 0.05, 0.00)
    for preferred in preferred_order:
        match = next(
            (row for row in pool if abs(float(row["min_evidence_score"]) - preferred) < 1e-9),
            None,
        )
        if match is not None:
            return float(match["min_evidence_score"])
    ranked = sorted(
        pool,
        key=lambda row: (
            float(row["false_abstain_rate"]),
            float(row["hallucination_rate"]),
            -float(row["min_evidence_score"]),
        ),
    )
    return float(ranked[0]["min_evidence_score"])


def _recommend_top_k(sweep: list[dict[str, Any]], *, configured_top_k: int) -> int:
    """Smallest k that reaches the maximum observed Hit@k (prefer MRR tie-break)."""
    if not sweep:
        return configured_top_k
    best_hit = max((row["hit_at_k"] or 0.0) for row in sweep)
    candidates = [row for row in sweep if (row["hit_at_k"] or 0.0) >= best_hit - 1e-9]
    candidates.sort(key=lambda row: (row["top_k"], -(row["mrr"] or 0.0)))
    return int(candidates[0]["top_k"])


def _gold_hit(item: QuestionRunResult) -> Any:
    for hit in item.retrieved:
        if hit.chunk_id == item.expected_chunk_id:
            return hit
    return None


def _question_row(item: QuestionRunResult) -> dict[str, Any]:
    gold = _gold_hit(item)
    top1 = item.retrieved[0] if item.retrieved else None
    max_score = max((hit.score for hit in item.retrieved), default=None)
    return {
        "question_id": item.question_id,
        "cohort": item.cohort.value if hasattr(item.cohort, "value") else str(item.cohort),
        "robustness_kind": item.robustness_kind,
        "hit_at_k": item.hit_at_k,
        "mrr": item.mrr,
        "retrieval_rank": item.retrieval_rank,
        "retrieval_latency_ms": item.retrieval_latency_ms,
        "retrieved_chunk_ids": [hit.chunk_id for hit in item.retrieved],
        "scores": [hit.score for hit in item.retrieved],
        "ranks": [hit.rank for hit in item.retrieved],
        "max_score": max_score,
        "top1_score": top1.score if top1 else None,
        "gold_chunk_score": gold.score if gold else None,
        "distance_to_correct_chunk": ((1.0 - float(gold.score)) if gold is not None else None),
        "rank_distance_to_correct": ((int(gold.rank) - 1) if gold is not None else None),
        "abstained": item.abstained,
        "hallucination_risk_estimate": item.hallucination_risk_estimate,
    }


def _score_stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "mean": None, "max": None, "p50": None}
    ordered = sorted(values)
    mid = len(ordered) // 2
    p50 = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
    return {
        "min": ordered[0],
        "mean": sum(ordered) / len(ordered),
        "max": ordered[-1],
        "p50": p50,
    }


def _histogram(values: list[float], *, bin_width: float) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for score in values:
        start = int(score / bin_width) * bin_width
        end = start + bin_width
        label = f"{start:.2f}-{end:.2f}"
        counts[label] += 1
    return dict(sorted(counts.items()))


def _tokens(text: str) -> list[str]:
    return [part for part in text.replace("\u200c", " ").split() if part]
