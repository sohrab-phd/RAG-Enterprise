"""Root-cause labeling for failed Persian RAG questions."""

from __future__ import annotations

from tools.persian_rag_benchmark.diagnostics.retrieval import explain_retrieval_failure
from tools.persian_rag_benchmark.models import FailureLabel, QuestionRunResult


def assign_root_causes(results: list[QuestionRunResult]) -> list[QuestionRunResult]:
    updated: list[QuestionRunResult] = []
    for result in results:
        labels, explanation, passed = _analyze(result)
        updated.append(
            result.model_copy(
                update={
                    "failure_labels": labels,
                    "failure_explanation": explanation,
                    "passed": passed,
                }
            )
        )
    return updated


def _analyze(result: QuestionRunResult) -> tuple[list[FailureLabel], str | None, bool]:
    labels: list[FailureLabel] = []

    if result.language_issues:
        if "arabic_yeh_or_kaf" in result.language_issues:
            labels.append(FailureLabel.TEXT_NORMALIZATION)
        if "not_nfc" in result.language_issues or "needs_nfkc" in result.language_issues:
            labels.append(FailureLabel.UNICODE_NORMALIZATION)
        if (
            "differs_from_production_normalize" in result.language_issues
            and not result.retrieval_hit
        ):
            labels.append(FailureLabel.HALFSPACE_NORMALIZATION)
        if result.detected_language not in {"fa", "unknown", None}:
            labels.append(FailureLabel.LANGUAGE_DETECTION)

    if not result.retrieval_hit and result.expected_chunk_id:
        labels.append(FailureLabel.RETRIEVAL)
        if result.correct_document:
            labels.append(FailureLabel.WRONG_CHUNK)
        else:
            labels.append(FailureLabel.WRONG_DOCUMENT)
        if result.avg_retrieval_score is not None and result.avg_retrieval_score < 0.15:
            labels.append(FailureLabel.LOW_RETRIEVAL_SCORE)

    if result.generated_answer is not None:
        scores = result.generation_scores
        if result.abstained and result.gold_answer:
            labels.append(FailureLabel.GENERATION)
        if scores.get("hallucination_risk"):
            labels.append(FailureLabel.GENERATION)
        if scores.get("citation_accuracy") is False and result.expected_chunk_id:
            labels.append(FailureLabel.CITATION)
        numeric = scores.get("numeric_accuracy")
        if isinstance(numeric, (int, float)) and float(numeric) < 1.0:
            labels.append(FailureLabel.GENERATION)

    if result.robustness_kind != "normal" and not result.retrieval_hit:
        labels.append(FailureLabel.EMBEDDING)

    unique_labels = list(dict.fromkeys(labels))
    passed = _is_pass(result)
    explanation: str | None = None
    if not passed:
        if not unique_labels:
            unique_labels.append(FailureLabel.UNKNOWN)
        explanation = _explain(result, unique_labels)
    return unique_labels, explanation, passed


def _is_pass(result: QuestionRunResult) -> bool:
    if result.expected_chunk_id and not result.retrieval_hit:
        return False
    if result.generated_answer is None:
        return bool(result.retrieval_hit or not result.expected_chunk_id)
    if result.generation_scores.get("hallucination_risk"):
        return False
    weak = float(result.generation_scores.get("semantic_similarity") or 0) < 0.2
    return not (result.gold_answer and weak)


def _explain(result: QuestionRunResult, labels: list[FailureLabel]) -> str:
    parts: list[str] = []
    retrieval_reason = explain_retrieval_failure(result)
    if retrieval_reason:
        parts.append(retrieval_reason)
    if (
        FailureLabel.TEXT_NORMALIZATION in labels
        or FailureLabel.UNICODE_NORMALIZATION in labels
        or FailureLabel.HALFSPACE_NORMALIZATION in labels
    ):
        parts.append(
            "پرسش به‌خاطر تفاوت نویسه‌های عربی/فارسی، نیم‌فاصله یا نرمال‌سازی یونیکد، "
            "ممکن است فضای embedding متفاوتی نسبت به قطعهٔ فارسی نرمال‌شده داشته باشد."
        )
    if FailureLabel.CITATION in labels:
        parts.append("پاسخ تولیدشده استنادِ قطعهٔ مورد انتظار را برنگرداند.")
    if FailureLabel.GENERATION in labels:
        parts.append(
            "پاسخ تولیدشده از نظر شباهت معنایی/عددی با پاسخ طلایی فاصله دارد "
            "یا با وجود شواهد، مدل مردد شده است."
        )
    if FailureLabel.EMBEDDING in labels:
        parts.append(
            "گونهٔ استحکام فارسی همان پرسش را به قطعهٔ دیگری هدایت کرد؛ "
            "حساسیت embedding به تنوع سطحی فارسی محتمل است."
        )
    if not parts:
        parts.append("علت دقیق نامشخص است؛ نیاز به بررسی دستی دارد.")
    label_text = ", ".join(label.value for label in labels)
    return f"[{label_text}] " + " ".join(parts)
