"""Generation quality diagnostics (Persian-aware, deterministic)."""

from __future__ import annotations

import re
from statistics import mean

from tools.persian_rag_benchmark.models import QuestionRunResult
from tools.persian_rag_benchmark.persian_text import (
    extract_numbers,
    to_latin_digits,
)


def score_answer(
    *,
    gold: str,
    predicted: str | None,
    expected_chunk_id: str,
    cited_chunk_ids: list[str],
    expected_citation_text: str,
    category: str,
) -> dict[str, float | bool | None]:
    if not predicted:
        return {
            "exact_match": False,
            "semantic_similarity": 0.0,
            "completeness": 0.0,
            "groundedness": False,
            "hallucination_risk": True,
            "citation_accuracy": False,
            "numeric_accuracy": None,
            "entity_accuracy": None,
            "procedure_accuracy": None,
            "language_quality": 0.0,
            "persian_fluency": 0.0,
            "terminology_consistency": 0.0,
        }

    gold_n = _normalize(gold)
    pred_n = _normalize(predicted)
    token_overlap = _jaccard(gold_n, pred_n)
    exact = gold_n == pred_n
    citation_ok = expected_chunk_id in cited_chunk_ids if expected_chunk_id else False
    grounded = citation_ok and token_overlap >= 0.15
    hallucination = token_overlap < 0.05 and not citation_ok

    gold_nums = {to_latin_digits(item) for item in extract_numbers(gold)}
    pred_nums = {to_latin_digits(item) for item in extract_numbers(predicted)}
    numeric = len(gold_nums & pred_nums) / len(gold_nums) if gold_nums else None

    citation_span_hit = (
        _normalize(expected_citation_text)[:40] in pred_n if expected_citation_text else None
    )
    persian_ratio = _persian_char_ratio(predicted)
    return {
        "exact_match": exact,
        "semantic_similarity": token_overlap,
        "completeness": min(1.0, len(pred_n.split()) / max(1, len(gold_n.split()))),
        "groundedness": grounded,
        "hallucination_risk": hallucination,
        "citation_accuracy": citation_ok,
        "numeric_accuracy": numeric,
        "entity_accuracy": token_overlap if category in {"responsibility", "permission"} else None,
        "procedure_accuracy": token_overlap if category in {"procedure", "multi_step"} else None,
        "language_quality": persian_ratio,
        "persian_fluency": persian_ratio * (0.7 + 0.3 * (1.0 if "  " not in predicted else 0.4)),
        "terminology_consistency": token_overlap,
        "citation_span_hit": citation_span_hit,
    }


def evaluate_generation(results: list[QuestionRunResult]) -> dict[str, object]:
    answered = [item for item in results if item.generated_answer is not None]
    if not answered:
        return {"n": 0}

    def _mean(key: str) -> float | None:
        values = [
            float(item.generation_scores[key])
            for item in answered
            if isinstance(item.generation_scores.get(key), (int, float))
        ]
        return mean(values) if values else None

    return {
        "n": len(answered),
        "exact_match_rate": mean(
            1.0 if item.generation_scores.get("exact_match") else 0.0 for item in answered
        ),
        "semantic_similarity_mean": _mean("semantic_similarity"),
        "completeness_mean": _mean("completeness"),
        "groundedness_rate": mean(
            1.0 if item.generation_scores.get("groundedness") else 0.0 for item in answered
        ),
        "hallucination_rate": mean(
            1.0 if item.generation_scores.get("hallucination_risk") else 0.0 for item in answered
        ),
        "citation_accuracy_rate": mean(
            1.0 if item.generation_scores.get("citation_accuracy") else 0.0 for item in answered
        ),
        "numeric_accuracy_mean": _mean("numeric_accuracy"),
        "persian_fluency_mean": _mean("persian_fluency"),
        "language_quality_mean": _mean("language_quality"),
        "abstention_rate": mean(1.0 if item.abstained else 0.0 for item in answered),
    }


def _normalize(text: str) -> str:
    text = to_latin_digits(text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


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
