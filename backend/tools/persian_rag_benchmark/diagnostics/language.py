"""Persian language surface diagnostics."""

from __future__ import annotations

from collections import Counter

from rag_enterprise.processing.language import detect_language
from rag_enterprise.processing.normalization import normalize_persian_text
from tools.persian_rag_benchmark.models import QuestionRunResult
from tools.persian_rag_benchmark.persian_text import diagnose_language_surface


def evaluate_language(results: list[QuestionRunResult]) -> dict[str, object]:
    issue_counter: Counter[str] = Counter()
    detection_mismatch = 0
    normalize_delta = 0
    for result in results:
        for issue in result.language_issues or diagnose_language_surface(result.question):
            issue_counter[issue] += 1
        detected = result.detected_language or detect_language(result.question)
        if detected not in {"fa", "unknown"} and _has_persian(result.question):
            detection_mismatch += 1
        if result.normalized_question != result.question:
            normalize_delta += 1
        # Production normalize vs raw robustness variants should usually differ for arabic letters.
        _ = normalize_persian_text(result.question)

    total = max(1, len(results))
    return {
        "n": len(results),
        "issue_counts": dict(issue_counter),
        "normalize_delta_rate": normalize_delta / total,
        "language_detection_mismatch_rate": detection_mismatch / total,
        "fa_detected_rate": mean_fa(results),
        "failures": [
            {
                "question_id": item.question_id,
                "issues": item.language_issues,
                "detected_language": item.detected_language,
            }
            for item in results
            if item.language_issues
        ][:50],
    }


def mean_fa(results: list[QuestionRunResult]) -> float:
    if not results:
        return 0.0
    return sum(1 for item in results if item.detected_language == "fa") / len(results)


def _has_persian(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06ff" for ch in text)
