"""Mathematically standard IR metrics (single- or multi-relevant)."""

from __future__ import annotations

from statistics import mean


def hit_at_k(retrieved_ids: list[str], expected_ids: list[str], *, k: int) -> float:
    """1.0 if any expected id appears in retrieved[:k], else 0.0."""
    if not expected_ids or k <= 0:
        return 0.0
    top = set(retrieved_ids[:k])
    return 1.0 if top.intersection(expected_ids) else 0.0


def recall_at_k(retrieved_ids: list[str], expected_ids: list[str], *, k: int) -> float:
    """|expected ∩ retrieved[:k]| / |expected|."""
    if not expected_ids or k <= 0:
        return 0.0
    expected = set(expected_ids)
    top = set(retrieved_ids[:k])
    return len(expected & top) / len(expected)


def precision_at_k(retrieved_ids: list[str], expected_ids: list[str], *, k: int) -> float:
    """|expected ∩ retrieved[:k]| / k  (denominator is always k)."""
    if k <= 0:
        return 0.0
    expected = set(expected_ids)
    top = set(retrieved_ids[:k])
    return len(expected & top) / k


def reciprocal_rank(retrieved_ids: list[str], expected_ids: list[str]) -> float:
    """1/rank of first hit; 0 if none."""
    expected = set(expected_ids)
    if not expected:
        return 0.0
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in expected:
            return 1.0 / rank
    return 0.0


def aggregate_ir(
    per_question: list[dict[str, float]],
) -> dict[str, float | int | None]:
    """Mean Hit@k / Recall@k / Precision@k / MRR over questions."""
    if not per_question:
        return {
            "n": 0,
            "hit_at_k": None,
            "recall_at_k": None,
            "precision_at_k": None,
            "mrr": None,
        }
    return {
        "n": len(per_question),
        "hit_at_k": mean(item["hit_at_k"] for item in per_question),
        "recall_at_k": mean(item["recall_at_k"] for item in per_question),
        "precision_at_k": mean(item["precision_at_k"] for item in per_question),
        "mrr": mean(item["mrr"] for item in per_question),
    }
