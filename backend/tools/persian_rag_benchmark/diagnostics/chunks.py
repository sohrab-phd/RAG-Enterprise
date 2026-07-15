"""Chunk corpus diagnostics for Persian documents."""

from __future__ import annotations

from collections import Counter
from statistics import mean

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

    by_document: dict[str, list[ChunkSnapshot]] = {}
    for chunk in chunks:
        by_document.setdefault(str(chunk.document_id), []).append(chunk)

    rows: list[dict[str, object]] = []
    never: list[str] = []
    lengths: list[int] = []
    tokens: list[int] = []
    sentences: list[int] = []
    paragraphs: list[int] = []
    overlaps: list[int] = []

    for document_id, doc_chunks in by_document.items():
        ordered = sorted(doc_chunks, key=lambda item: item.sequence_number)
        for index, chunk in enumerate(ordered):
            cid = str(chunk.chunk_id)
            freq = retrieval_freq.get(cid, 0)
            if freq == 0:
                never.append(cid)
            text = chunk.text
            sentence_count = len(split_persian_sentences(text))
            paragraph_count = max(1, len([p for p in text.split("\n\n") if p.strip()]))
            token_count = token_estimate(text)
            overlap_size = _inter_chunk_overlap(ordered, index)
            lengths.append(len(text))
            tokens.append(token_count)
            sentences.append(sentence_count)
            paragraphs.append(paragraph_count)
            overlaps.append(overlap_size)
            rows.append(
                {
                    "chunk_id": cid,
                    "document_id": document_id,
                    "chunk_index": chunk.sequence_number,
                    "length_chars": len(text),
                    "estimated_token_count": token_count,
                    "sentence_count": sentence_count,
                    "paragraph_count": paragraph_count,
                    "overlap_size": overlap_size,
                    "heading_detected": bool(chunk.heading),
                    "heading": chunk.heading,
                    "language": chunk.language,
                    "start_offset": chunk.start_offset,
                    "end_offset": chunk.end_offset,
                    "retrieval_frequency": freq,
                    "looks_like_table": looks_like_table(text),
                    "looks_like_list": looks_like_list(text),
                    "quality_flags": _quality_flags(text),
                }
            )

    chunks_per_document = [len(items) for items in by_document.values()]
    return {
        "chunk_count": len(chunks),
        "document_count": len(by_document),
        "avg_chunks_per_document": (mean(chunks_per_document) if chunks_per_document else 0.0),
        "avg_chunk_chars": mean(lengths) if lengths else 0.0,
        "avg_estimated_tokens": mean(tokens) if tokens else 0.0,
        "avg_sentence_count": mean(sentences) if sentences else 0.0,
        "avg_paragraph_count": mean(paragraphs) if paragraphs else 0.0,
        "avg_overlap_size": mean(overlaps) if overlaps else 0.0,
        "chunk_size_histogram": _histogram(
            lengths, [0, 200, 400, 600, 800, 1000, 1200, 1500, 10_000]
        ),
        "overlap_distribution": _histogram(overlaps, [0, 1, 50, 100, 125, 150, 200, 10_000]),
        "sentence_distribution": _histogram(sentences, [0, 1, 2, 3, 5, 8, 13, 100]),
        "never_retrieved_count": len(never),
        "never_retrieved_chunk_ids": never[:50],
        "frequently_retrieved": [
            {"chunk_id": chunk_id, "count": count}
            for chunk_id, count in retrieval_freq.most_common(10)
        ],
        "chunks": rows,
    }


def _inter_chunk_overlap(ordered: list[ChunkSnapshot], index: int) -> int:
    if index <= 0:
        return 0
    previous = ordered[index - 1]
    current = ordered[index]
    return max(0, previous.end_offset - current.start_offset)


def _histogram(values: list[int], edges: list[int]) -> dict[str, int]:
    buckets = {f"{edges[i]}-{edges[i + 1] - 1}": 0 for i in range(len(edges) - 1)}
    keys = list(buckets)
    for value in values:
        placed = False
        for i in range(len(edges) - 1):
            if edges[i] <= value < edges[i + 1]:
                buckets[keys[i]] += 1
                placed = True
                break
        if not placed and keys:
            buckets[keys[-1]] += 1
    return buckets


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
