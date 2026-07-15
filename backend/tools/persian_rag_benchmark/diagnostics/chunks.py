"""Chunk corpus diagnostics for Persian documents."""

from __future__ import annotations

from collections import Counter

from tools.persian_rag_benchmark.models import ChunkSnapshot, QuestionRunResult
from tools.persian_rag_benchmark.persian_text import (
    looks_like_list,
    looks_like_table,
    split_persian_sentences,
    token_estimate,
)


def diagnose_chunks(
    chunks: list[ChunkSnapshot],
    results: list[QuestionRunResult],
) -> dict[str, object]:
    retrieval_freq: Counter[str] = Counter()
    for result in results:
        for evidence in result.retrieved:
            retrieval_freq[evidence.chunk_id] += 1

    rows: list[dict[str, object]] = []
    never: list[str] = []
    for chunk in chunks:
        cid = str(chunk.chunk_id)
        freq = retrieval_freq.get(cid, 0)
        if freq == 0:
            never.append(cid)
        text = chunk.text
        rows.append(
            {
                "chunk_id": cid,
                "document_id": str(chunk.document_id),
                "length_chars": len(text),
                "sentence_count": len(split_persian_sentences(text)),
                "token_estimate": token_estimate(text),
                "language": chunk.language,
                "overlap_hint": max(0, chunk.end_offset - chunk.start_offset),
                "retrieval_frequency": freq,
                "looks_like_table": looks_like_table(text),
                "looks_like_list": looks_like_list(text),
                "heading": chunk.heading,
                "quality_flags": _quality_flags(text),
            }
        )

    frequent = retrieval_freq.most_common(10)
    return {
        "chunk_count": len(chunks),
        "never_retrieved_count": len(never),
        "never_retrieved_chunk_ids": never[:50],
        "frequently_retrieved": [
            {"chunk_id": chunk_id, "count": count} for chunk_id, count in frequent
        ],
        "chunks": rows,
        "avg_chunk_chars": (
            sum(len(chunk.text) for chunk in chunks) / len(chunks) if chunks else 0
        ),
    }


def _quality_flags(text: str) -> list[str]:
    flags: list[str] = []
    lines = [line for line in text.splitlines() if line.strip()]
    if lines and sum(1 for line in lines if len(line) < 12) / len(lines) > 0.45:
        flags.append("fragmented_short_lines")
    if "  " in text:
        flags.append("double_spaces")
    if looks_like_table(text):
        flags.append("table_like")
    if looks_like_list(text):
        flags.append("list_like")
    if len(text) < 80:
        flags.append("very_short")
    if len(text) > 2500:
        flags.append("very_long")
    return flags
