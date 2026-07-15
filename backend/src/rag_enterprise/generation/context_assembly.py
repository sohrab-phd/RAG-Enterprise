"""Assemble cleaner generation context from dense retrieval hits.

Sits between RetrievalService results and PromptBuilder composition.
Deterministic: no reranking scores, only dedupe / neighbor merge / ordering.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from rag_enterprise.retrieval.models import RetrievedChunk

# Near-duplicate thresholds (deterministic, no ML).
_CONTAINMENT_RATIO = 0.85
_TOKEN_JACCARD_DUP = 0.92

_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ContextBlock:
    """One evidence block sent to the prompt (may merge consecutive neighbors)."""

    heading: str | None
    chunks: tuple[RetrievedChunk, ...]
    merged_text: str
    primary: RetrievedChunk

    @property
    def source_chunk_ids(self) -> tuple[uuid.UUID, ...]:
        return tuple(chunk.chunk_id for chunk in self.chunks)

    @property
    def max_score(self) -> float:
        return max(chunk.score for chunk in self.chunks)

    @property
    def document_id(self) -> uuid.UUID:
        return self.chunks[0].document_id

    @property
    def document_version_id(self) -> uuid.UUID:
        return self.chunks[0].document_version_id

    @property
    def min_chunk_index(self) -> int:
        return min(chunk.chunk_index for chunk in self.chunks)


@dataclass(frozen=True)
class ContextAssemblyResult:
    """Assembled context plus diagnostics for benchmarks."""

    blocks: tuple[ContextBlock, ...]
    chunks_for_citations: tuple[RetrievedChunk, ...]
    original_chunk_ids: tuple[uuid.UUID, ...]
    duplicate_removed_ids: tuple[uuid.UUID, ...]
    duplicated_chars_removed: int
    context_char_count: int
    estimated_token_count: int

    @property
    def original_chunk_count(self) -> int:
        return len(self.original_chunk_ids)

    @property
    def kept_chunk_count(self) -> int:
        return len(self.chunks_for_citations)

    @property
    def duplicate_removal_count(self) -> int:
        return len(self.duplicate_removed_ids)

    @property
    def merged_source_chunk_count(self) -> int:
        return sum(len(block.chunks) for block in self.blocks)

    def to_diagnostics(self) -> dict[str, object]:
        return {
            "original_chunk_ids": [str(item) for item in self.original_chunk_ids],
            "kept_chunk_ids": [str(item.chunk_id) for item in self.chunks_for_citations],
            "duplicate_removed_ids": [str(item) for item in self.duplicate_removed_ids],
            "duplicate_removals": self.duplicate_removal_count,
            "duplicated_chars_removed": self.duplicated_chars_removed,
            "original_chunk_count": self.original_chunk_count,
            "final_block_count": len(self.blocks),
            "merged_source_chunk_count": self.merged_source_chunk_count,
            "context_char_count": self.context_char_count,
            "estimated_token_count": self.estimated_token_count,
            "blocks": [
                {
                    "heading": block.heading,
                    "chunk_ids": [str(item) for item in block.source_chunk_ids],
                    "chunk_indexes": [chunk.chunk_index for chunk in block.chunks],
                    "primary_chunk_id": str(block.primary.chunk_id),
                    "max_score": block.max_score,
                    "merged_chars": len(block.merged_text),
                }
                for block in self.blocks
            ],
        }


def assemble_context(chunks: list[RetrievedChunk]) -> ContextAssemblyResult:
    """Dedupe → order (score, heading, neighbor) → merge consecutive neighbors."""
    original_ids = tuple(chunk.chunk_id for chunk in chunks)
    kept, removed, dup_chars = _dedupe_chunks(chunks)
    ordered = _order_chunks(kept)
    blocks = _merge_neighbor_blocks(ordered)
    context_chars = sum(len(block.merged_text) for block in blocks)
    citation_chunks = tuple(chunk for block in blocks for chunk in block.chunks)
    return ContextAssemblyResult(
        blocks=blocks,
        chunks_for_citations=citation_chunks,
        original_chunk_ids=original_ids,
        duplicate_removed_ids=tuple(removed),
        duplicated_chars_removed=dup_chars,
        context_char_count=context_chars,
        estimated_token_count=_estimate_tokens(context_chars),
    )


def _dedupe_chunks(
    chunks: list[RetrievedChunk],
) -> tuple[list[RetrievedChunk], list[uuid.UUID], int]:
    """Drop near-duplicates; keep higher-score (earlier in retrieval order)."""
    kept: list[RetrievedChunk] = []
    removed: list[uuid.UUID] = []
    dup_chars = 0
    for chunk in chunks:
        duplicate_of: RetrievedChunk | None = None
        for existing in kept:
            if _is_near_duplicate(chunk.text, existing.text):
                duplicate_of = existing
                break
        if duplicate_of is None:
            kept.append(chunk)
            continue
        removed.append(chunk.chunk_id)
        dup_chars += len(chunk.text.strip())
    return kept, removed, dup_chars


def _order_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Deterministic presentation order.

    Primary: retrieval score (desc).
    Secondary: heading continuity (same heading groups).
    Tertiary: document / neighboring chunk_index.
    """
    return sorted(
        chunks,
        key=lambda chunk: (
            -chunk.score,
            (chunk.heading or "").casefold(),
            str(chunk.document_version_id),
            chunk.chunk_index,
            str(chunk.chunk_id),
        ),
    )


def _merge_neighbor_blocks(chunks: list[RetrievedChunk]) -> tuple[ContextBlock, ...]:
    """Merge consecutive same-document / same-heading neighbors into blocks."""
    if not chunks:
        return ()

    # Build merge chains in document order, then sort chains by score.
    by_doc: dict[uuid.UUID, list[RetrievedChunk]] = {}
    for chunk in chunks:
        by_doc.setdefault(chunk.document_version_id, []).append(chunk)

    chains: list[list[RetrievedChunk]] = []
    for group in by_doc.values():
        group_sorted = sorted(
            group,
            key=lambda item: (item.chunk_index, str(item.chunk_id)),
        )
        current: list[RetrievedChunk] = [group_sorted[0]]
        for chunk in group_sorted[1:]:
            previous = current[-1]
            if _can_merge(previous, chunk):
                current.append(chunk)
            else:
                chains.append(current)
                current = [chunk]
        chains.append(current)

    blocks = [_to_block(chain) for chain in chains]
    blocks.sort(
        key=lambda block: (
            -block.max_score,
            (block.heading or "").casefold(),
            str(block.document_version_id),
            block.min_chunk_index,
            str(block.primary.chunk_id),
        )
    )
    return tuple(blocks)


def _can_merge(left: RetrievedChunk, right: RetrievedChunk) -> bool:
    """Merge consecutive neighbors from the same document version."""
    if left.document_version_id != right.document_version_id:
        return False
    return right.chunk_index == left.chunk_index + 1


def _heading_key(heading: str | None) -> str:
    return (heading or "").strip().casefold()


def _to_block(chain: list[RetrievedChunk]) -> ContextBlock:
    ordered = sorted(chain, key=lambda item: (item.chunk_index, str(item.chunk_id)))
    primary = max(ordered, key=lambda item: (item.score, -item.chunk_index, str(item.chunk_id)))
    merged = ordered[0].text.strip()
    for chunk in ordered[1:]:
        merged = _join_adjacent(merged, chunk.text)
    # Prefer a stable heading when all sources agree; else primary heading.
    headings = {_heading_key(chunk.heading) for chunk in ordered}
    if len(headings) == 1:
        heading = next((chunk.heading for chunk in ordered if chunk.heading), None)
    else:
        heading = primary.heading
    return ContextBlock(
        heading=heading,
        chunks=tuple(ordered),
        merged_text=merged,
        primary=primary,
    )


def _join_adjacent(left: str, right: str) -> str:
    left_s = left.strip()
    right_s = right.strip()
    if not left_s:
        return right_s
    if not right_s:
        return left_s
    max_overlap = min(len(left_s), len(right_s))
    for size in range(max_overlap, 0, -1):
        if left_s.endswith(right_s[:size]):
            return f"{left_s}{right_s[size:]}"
    return f"{left_s}\n{right_s}"


def _is_near_duplicate(left: str, right: str) -> bool:
    a = _normalize_text(left)
    b = _normalize_text(right)
    if not a or not b:
        return False
    if a == b:
        return True
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if shorter in longer and (len(shorter) / len(longer)) >= _CONTAINMENT_RATIO:
        return True
    return _token_jaccard(a, b) >= _TOKEN_JACCARD_DUP


def _normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.strip()).casefold()


def _token_jaccard(left: str, right: str) -> float:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return intersection / union if union else 0.0


def _estimate_tokens(char_count: int) -> int:
    """Rough token estimate without external tokenizers (chars/4)."""
    if char_count <= 0:
        return 0
    return max(1, (char_count + 3) // 4)
