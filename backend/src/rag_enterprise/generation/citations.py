"""Citation extraction, abstention detection, and answer sanitization."""

from __future__ import annotations

import re
import uuid

from rag_enterprise.generation.models import Citation
from rag_enterprise.retrieval.models import RetrievedChunk

_MARKER_RE = re.compile(r"\[(\d+)\]")
# Accept common LLM abstain variants, including trailing junk / citations.
_ABSTAIN_LINE_RE = re.compile(
    r"^\s*ABSTAIN\b\s*:?\s*(?P<reason>[A-Za-z][\w-]*)?\b",
    re.IGNORECASE,
)
_ABSTAIN_ANYWHERE_RE = re.compile(
    r"\bABSTAIN\b\s*:?\s*(?P<reason>[A-Za-z][\w-]*)?\b",
    re.IGNORECASE,
)
_NON_CONTENT_RE = re.compile(r"\[\d+\]|\s+")


def is_model_abstention(content: str) -> str | None:
    """Return abstention reason code if the model abstained.

    Detects fragile LLM variants such as::

        ABSTAIN
        ABSTAIN:
        ABSTAIN: insufficient_evidence
        ABSTAIN: insufficient_evidence [1]
        ABSTAIN : insufficient_evidence
        ABSTAIN:\\ninsufficient_evidence

    Never returns ``None`` when the reply is clearly an ABSTAIN directive, so
    raw model abstain text cannot leak as a completed answer.
    """
    text = (content or "").strip()
    if not text:
        return None

    # Prefer a leading ABSTAIN line (possibly multiline reason).
    first_line, _, rest = text.partition("\n")
    match = _ABSTAIN_LINE_RE.match(first_line)
    # "ABSTAIN:" on first line, reason on the next.
    if (
        match is None
        and rest.strip()
        and re.match(r"^\s*ABSTAIN\b\s*:?\s*$", first_line, re.IGNORECASE)
    ):
        reason_match = re.match(
            r"^\s*(?P<reason>[A-Za-z][\w-]*)\b",
            rest.strip(),
            re.IGNORECASE,
        )
        if reason_match is not None:
            return reason_match.group("reason").lower()
        return "insufficient_evidence"
    if match is not None:
        reason = match.group("reason")
        return (reason or "insufficient_evidence").lower()

    # Whole-message ABSTAIN (model mixed junk / citations around the token).
    anywhere = _ABSTAIN_ANYWHERE_RE.search(text)
    if anywhere is not None:
        # Only treat as abstain when ABSTAIN dominates the message (not a
        # normal answer that happens to mention the word).
        without_abstain = _ABSTAIN_ANYWHERE_RE.sub(" ", text)
        remainder = _NON_CONTENT_RE.sub("", without_abstain)
        if len(remainder) <= 24:
            reason = anywhere.group("reason")
            return (reason or "insufficient_evidence").lower()

    return None


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


def strip_question_echo(question: str, answer: str) -> str:
    """Remove a leading copy of the question from the model answer."""
    q = (question or "").strip()
    a = (answer or "").strip()
    if not q or not a:
        return a

    # Exact / whitespace-insensitive prefix echo.
    q_compact = re.sub(r"\s+", " ", q).strip()
    a_compact = re.sub(r"\s+", " ", a).strip()
    if a_compact.lower().startswith(q_compact.lower()):
        trimmed = a_compact[len(q_compact) :].lstrip(" :-–—\n\t")
        return trimmed.strip() if trimmed.strip() else a

    # First-line echo (common with Persian FAQ models).
    first_line, _, rest = a.partition("\n")
    if first_line.strip() and first_line.strip() == q:
        return rest.strip() if rest.strip() else a
    return a


def is_substantive_answer(answer: str) -> bool:
    """True when the answer has usable prose beyond citation markers."""
    text = _MARKER_RE.sub(" ", answer or "")
    text = re.sub(r"\s+", " ", text).strip()
    return len(text) >= 8


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


def salvage_top_chunk_citation(
    *,
    chunks: list[RetrievedChunk],
    markers: dict[str, uuid.UUID],
    excerpt_chars: int = 240,
) -> list[Citation] | None:
    """Attach the highest-scoring prompt chunk when the model omitted markers.

    Used only when evidence was already accepted by the sufficiency gate and the
    model produced a substantive non-abstain answer. Prevents false abstains from
    ``citation_validation_failed`` without inventing facts.
    """
    if not chunks:
        return None
    # Prefer marker "1" (primary evidence block) when present.
    preferred_id = markers.get("1")
    chunk: RetrievedChunk | None = None
    if preferred_id is not None:
        chunk = next((item for item in chunks if item.chunk_id == preferred_id), None)
    if chunk is None:
        chunk = max(chunks, key=lambda item: item.score)
    excerpt = chunk.text.strip()
    if len(excerpt) > excerpt_chars:
        excerpt = excerpt[:excerpt_chars] + "…"
    return [
        Citation(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            document_version_id=chunk.document_version_id,
            rank=1,
            relevance_score=chunk.score,
            excerpt=excerpt,
            start_char=chunk.start_char,
            end_char=chunk.end_char,
            marker="[1]",
        )
    ]
