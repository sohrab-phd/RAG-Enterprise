"""Aggregate context-assembly diagnostics across benchmark questions."""

from __future__ import annotations

from typing import Any

from tools.persian_rag_benchmark.models import QuestionRunResult


def evaluate_context_assembly(results: list[QuestionRunResult]) -> dict[str, Any]:
    """Summarize dedupe/merge/token impact for Measured and all answered questions."""
    with_ctx = [item for item in results if item.context_diagnostics]
    if not with_ctx:
        return {"n": 0, "skipped": True}

    original_counts: list[int] = []
    block_counts: list[int] = []
    dup_removals: list[int] = []
    dup_chars: list[int] = []
    token_counts: list[int] = []
    char_counts: list[int] = []
    prompt_chars: list[int] = []
    examples: list[dict[str, Any]] = []

    for item in with_ctx:
        diag = item.context_diagnostics
        original_counts.append(int(diag.get("original_chunk_count") or 0))
        block_counts.append(int(diag.get("final_block_count") or 0))
        dup_removals.append(int(diag.get("duplicate_removals") or 0))
        dup_chars.append(int(diag.get("duplicated_chars_removed") or 0))
        token_counts.append(int(diag.get("estimated_token_count") or 0))
        char_counts.append(int(diag.get("context_char_count") or 0))
        if isinstance(diag.get("final_prompt_chars"), int):
            prompt_chars.append(int(diag["final_prompt_chars"]))
        if len(examples) < 5:
            examples.append(
                {
                    "question_id": item.question_id,
                    "retrieved_chunk_ids": [hit.chunk_id for hit in item.retrieved],
                    "blocks": diag.get("blocks"),
                    "duplicate_removed_ids": diag.get("duplicate_removed_ids"),
                    "estimated_token_count": diag.get("estimated_token_count"),
                }
            )

    def _avg(values: list[int]) -> float | None:
        return (sum(values) / len(values)) if values else None

    return {
        "n": len(with_ctx),
        "avg_original_chunks": _avg(original_counts),
        "avg_final_blocks": _avg(block_counts),
        "avg_duplicate_removals": _avg(dup_removals),
        "avg_duplicated_chars_removed": _avg(dup_chars),
        "avg_context_char_count": _avg(char_counts),
        "avg_estimated_token_count": _avg(token_counts),
        "avg_final_prompt_chars": _avg(prompt_chars) if prompt_chars else None,
        "total_duplicate_removals": sum(dup_removals),
        "total_duplicated_chars_removed": sum(dup_chars),
        "examples": examples,
    }
