"""Generation quality diagnostics — Measured, Derived, and Heuristic fields."""

from __future__ import annotations

import re
from statistics import mean
from typing import Any

from tools.persian_rag_benchmark.models import QuestionRunResult
from tools.persian_rag_benchmark.persian_text import (
    extract_numbers,
    to_latin_digits,
)
from tools.persian_rag_benchmark.trust import EvaluationCohort, MetricTrust


def score_answer(
    *,
    gold: str,
    predicted: str | None,
    expected_chunk_id: str,
    cited_chunk_ids: list[str],
    category: str,
) -> dict[str, Any]:
    """Return named diagnostics with explicit heuristic vs derived semantics."""
    if not predicted:
        return {
            "exact_match": False,
            "lexical_overlap": 0.0,
            "heuristic_fluency_estimate": 0.0,
            "entity_match_estimate": None,
            "procedure_match_estimate": None,
            "groundedness_estimate": False,
            "hallucination_risk_estimate": True,
            "citation_accuracy": False,
            "numeric_accuracy": None,
        }

    gold_n = _normalize(gold)
    pred_n = _normalize(predicted)
    lexical = _jaccard(gold_n, pred_n)
    exact = gold_n == pred_n
    citation_ok = expected_chunk_id in cited_chunk_ids if expected_chunk_id else False
    grounded = citation_ok and lexical >= 0.15
    hallucination = lexical < 0.05 and not citation_ok

    gold_nums = {to_latin_digits(item) for item in extract_numbers(gold)}
    pred_nums = {to_latin_digits(item) for item in extract_numbers(predicted)}
    numeric = len(gold_nums & pred_nums) / len(gold_nums) if gold_nums else None

    persian_ratio = _persian_char_ratio(predicted)
    fluency = persian_ratio * (0.7 + 0.3 * (1.0 if "  " not in predicted else 0.4))

    return {
        "exact_match": exact,
        "lexical_overlap": lexical,
        "heuristic_fluency_estimate": fluency,
        "entity_match_estimate": (
            lexical if category in {"responsibility", "permission"} else None
        ),
        "procedure_match_estimate": (lexical if category in {"procedure", "multi_step"} else None),
        "groundedness_estimate": grounded,
        "hallucination_risk_estimate": hallucination,
        "citation_accuracy": citation_ok,
        "numeric_accuracy": numeric,
    }


def evaluate_generation_by_cohort(
    results: list[QuestionRunResult],
) -> dict[str, dict[str, Any]]:
    return {
        EvaluationCohort.BASELINE.value: _eval_subset(
            [item for item in results if item.cohort == EvaluationCohort.BASELINE]
        ),
        EvaluationCohort.ROBUSTNESS.value: _eval_subset(
            [item for item in results if item.cohort == EvaluationCohort.ROBUSTNESS]
        ),
    }


def _eval_subset(results: list[QuestionRunResult]) -> dict[str, Any]:
    answered = [item for item in results if item.generated_answer is not None]
    if not answered:
        return {"n": 0, "trust_notes": {}}

    def _mean(attr: str) -> float | None:
        values = [
            float(getattr(item, attr))
            for item in answered
            if isinstance(getattr(item, attr), (int, float))
        ]
        return mean(values) if values else None

    return {
        "n": len(answered),
        "exact_match_rate": {
            "value": mean(1.0 if item.exact_match else 0.0 for item in answered),
            "trust": MetricTrust.DERIVED.value,
        },
        "lexical_overlap_mean": {
            "value": _mean("lexical_overlap"),
            "trust": MetricTrust.HEURISTIC.value,
            "label": "Lexical Overlap (Heuristic)",
        },
        "heuristic_fluency_estimate_mean": {
            "value": _mean("heuristic_fluency_estimate"),
            "trust": MetricTrust.HEURISTIC.value,
            "label": "Heuristic Fluency Estimate",
        },
        "entity_match_estimate_mean": {
            "value": _mean("entity_match_estimate"),
            "trust": MetricTrust.HEURISTIC.value,
            "label": "Entity Match Estimate",
        },
        "procedure_match_estimate_mean": {
            "value": _mean("procedure_match_estimate"),
            "trust": MetricTrust.HEURISTIC.value,
            "label": "Procedure Match Estimate",
        },
        "groundedness_estimate_rate": {
            "value": mean(1.0 if item.groundedness_estimate else 0.0 for item in answered),
            "trust": MetricTrust.HEURISTIC.value,
            "label": "Groundedness Estimate (Heuristic)",
        },
        "citation_accuracy_rate": {
            "value": mean(1.0 if item.citation_accuracy else 0.0 for item in answered),
            "trust": MetricTrust.MEASURED.value,
        },
        "numeric_accuracy_mean": {
            "value": _mean("numeric_accuracy"),
            "trust": MetricTrust.DERIVED.value,
        },
        "abstention_rate": {
            "value": mean(1.0 if item.abstained else 0.0 for item in answered),
            "trust": MetricTrust.MEASURED.value,
        },
    }


def _normalize(text: str) -> str:
    text = to_latin_digits(text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _jaccard(left: str, right: str) -> float:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _persian_char_ratio(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha() or "\u0600" <= ch <= "\u06ff"]
    if not letters:
        return 0.0
    persian = sum(1 for ch in letters if "\u0600" <= ch <= "\u06ff")
    return persian / len(letters)
