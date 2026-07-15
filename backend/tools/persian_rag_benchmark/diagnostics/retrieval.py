"""Retrieval quality diagnostics."""

from __future__ import annotations

from collections import Counter
from statistics import mean

from tools.persian_rag_benchmark.models import QuestionRunResult


def evaluate_retrieval(results: list[QuestionRunResult], *, top_k: int) -> dict[str, object]:
    answerable = [item for item in results if item.expected_chunk_id]
    if not answerable:
        return {
            "n": 0,
            "hit_rate": None,
            "recall_at_k": None,
            "precision_at_k": None,
            "mrr": None,
            "avg_retrieval_score": None,
            "correct_document_rate": None,
            "correct_chunk_rate": None,
        }

    hits = [item for item in answerable if item.retrieval_hit]
    reciprocal_ranks: list[float] = []
    precisions: list[float] = []
    for item in answerable:
        if item.retrieval_rank is not None:
            reciprocal_ranks.append(1.0 / item.retrieval_rank)
        else:
            reciprocal_ranks.append(0.0)
        retrieved = {ev.chunk_id for ev in item.retrieved}
        expected = {item.expected_chunk_id}
        if retrieved:
            precisions.append(len(retrieved & expected) / min(top_k, len(retrieved)))
        else:
            precisions.append(0.0)

    scores = [
        item.avg_retrieval_score for item in answerable if item.avg_retrieval_score is not None
    ]
    return {
        "n": len(answerable),
        "hit_rate": len(hits) / len(answerable),
        "recall_at_k": len(hits) / len(answerable),
        "precision_at_k": mean(precisions) if precisions else None,
        "mrr": mean(reciprocal_ranks) if reciprocal_ranks else None,
        "avg_retrieval_score": mean(scores) if scores else None,
        "correct_document_rate": mean(1.0 if item.correct_document else 0.0 for item in answerable),
        "correct_chunk_rate": mean(1.0 if item.correct_chunk else 0.0 for item in answerable),
        "top_k": top_k,
        "failure_counts": dict(
            Counter("miss" if not item.retrieval_hit else "hit" for item in answerable)
        ),
    }


def explain_retrieval_failure(result: QuestionRunResult) -> str | None:
    if result.retrieval_hit:
        return None
    if not result.retrieved:
        return (
            "هیچ قطعه‌ای بازیابی نشد؛ ممکن است ایندکس خالی باشد، "
            "آستانه شباهت پایین باشد، یا زبان کوئری/قطعه ناسازگار باشد."
        )
    if result.correct_document and not result.correct_chunk:
        return (
            "سند صحیح بازیابی شد اما قطعهٔ طلایی در top-k نبود؛ "
            "احتمالاً قطعه‌بندی مرز معنایی فارسی را شکسته یا embedding پرسش را منحرف کرده است."
        )
    top = result.retrieved[0]
    return (
        f"قطعهٔ طلایی در رتبهٔ top-k نبود. بهترین نتیجه chunk={top.chunk_id} "
        f"با امتیاز {top.score:.4f} از سند {top.document_id} بود."
    )
