"""Citation extraction and validation."""

from __future__ import annotations

import re
import uuid

from rag_enterprise.generation.models import Citation
from rag_enterprise.retrieval.models import RetrievedChunk

_MARKER_RE = re.compile(r"\[(\d+)\]")
_ABSTAIN_RE = re.compile(r"^\s*ABSTAIN:\s*(\w+)\s*$", re.IGNORECASE | re.MULTILINE)


def is_model_abstention(content: str) -> str | None:
    """Return abstention reason code if the model abstained."""
    match = _ABSTAIN_RE.search(content.strip())
    if match is None:
        return None
    return match.group(1).lower()


def extract_markers(content: str) -> list[str]:
    """Return citation markers in order of first appearance."""
    seen: set[str] = set()
    ordered: list[str] = []
    for match in _MARKER_RE.finditer(content):
        marker = match.group(1)
        if marker not in seen:
            seen.add(marker)
            ordered.append(marker)
    return ordered


def validate_citations(
    *,
    answer: str,
    markers: dict[str, uuid.UUID],
    chunks: list[RetrievedChunk],
    excerpt_chars: int = 240,
) -> list[Citation] | None:
    """Map valid markers to citations; return None if none valid."""
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    citations: list[Citation] = []
    for rank, marker in enumerate(extract_markers(answer), start=1):
        chunk_id = markers.get(marker)
        if chunk_id is None:
            continue
        chunk = by_id.get(chunk_id)
        if chunk is None:
            continue
        excerpt = chunk.text.strip()
        if len(excerpt) > excerpt_chars:
            excerpt = excerpt[:excerpt_chars] + "…"
        citations.append(
            Citation(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_version_id=chunk.document_version_id,
                rank=rank,
                relevance_score=chunk.score,
                excerpt=excerpt,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                marker=f"[{marker}]",
            )
        )
    if not citations:
        return None
    return citations
