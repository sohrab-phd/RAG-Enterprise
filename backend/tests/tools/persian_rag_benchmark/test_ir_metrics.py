"""IR metric unit tests (isolated)."""

from __future__ import annotations

from tools.persian_rag_benchmark.ir_metrics import (
    aggregate_ir,
    hit_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_multi_relevant_recall_and_precision() -> None:
    retrieved = ["a", "b", "c", "d", "e"]
    expected = ["b", "z"]
    assert hit_at_k(retrieved, expected, k=3) == 1.0
    assert recall_at_k(retrieved, expected, k=3) == 0.5
    assert precision_at_k(retrieved, expected, k=3) == 1 / 3
    assert reciprocal_rank(retrieved, expected) == 0.5


def test_aggregate_ir_means() -> None:
    rows = [
        {"hit_at_k": 1.0, "recall_at_k": 1.0, "precision_at_k": 0.2, "mrr": 1.0},
        {"hit_at_k": 0.0, "recall_at_k": 0.0, "precision_at_k": 0.0, "mrr": 0.0},
    ]
    out = aggregate_ir(rows)
    assert out["n"] == 2
    assert out["hit_at_k"] == 0.5
    assert out["mrr"] == 0.5
