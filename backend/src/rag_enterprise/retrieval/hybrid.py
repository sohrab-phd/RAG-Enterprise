"""Hybrid fusion: dense ranks + BM25 ranks → Reciprocal Rank Fusion."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rag_enterprise.processing.normalization import normalize_persian_text
from rag_enterprise.retrieval.bm25 import BM25Hit, BM25Index, tokenize_lexical

_RRF_K = 60
_HYBRID_POOL = 30
_RC32_CANDIDATE_CAP = 24

_TOKEN_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)
_NUMBER_RE = re.compile(r"\d+(?:[./-]\d+)*")
_BROWSER_RE = re.compile(
    r"\b(google\s*chrome|chrome|firefox|mozilla|edge|safari)\b",
    re.IGNORECASE,
)
_COURSE_CODE_RE = re.compile(r"\b(?:گزارش\s*)?\d{1,3}\b")


@dataclass(frozen=True)
class RankedId:
    """One ranked identifier from a retrieval channel."""

    chunk_id: str
    rank: int
    score: float


@dataclass(frozen=True)
class HybridDiagnostics:
    """Explainable hybrid retrieval diagnostics for one query."""

    dense_top: tuple[RankedId, ...]
    bm25_top: tuple[RankedId, ...]
    rrf_top: tuple[RankedId, ...]
    rrf_k: int
    dense_pool: int
    bm25_pool: int

    def to_dict(self) -> dict[str, object]:
        return {
            "rrf_k": self.rrf_k,
            "dense_pool": self.dense_pool,
            "bm25_pool": self.bm25_pool,
            "dense_top": [_ranked_to_dict(item) for item in self.dense_top],
            "bm25_top": [_ranked_to_dict(item) for item in self.bm25_top],
            "rrf_top": [_ranked_to_dict(item) for item in self.rrf_top],
        }


def hybrid_pool_size() -> int:
    """Dense and BM25 candidate pool size before RRF."""
    return _HYBRID_POOL


def rc32_candidate_cap() -> int:
    """Max fused candidates passed into RC3.2 calibration."""
    return _RC32_CANDIDATE_CAP


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    *,
    k: int = _RRF_K,
) -> list[tuple[str, float]]:
    """Standard RRF: score = Σ 1/(k + rank). Deterministic tie-break by id."""
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, chunk_id in enumerate(ranked, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return ordered


def apply_persian_bm25_boosts(
    *,
    query: str,
    index: BM25Index,
    hits: list[BM25Hit],
) -> list[BM25Hit]:
    """Re-rank BM25 hits with Persian FAQ / entity boosts (deterministic)."""
    normalized_query = normalize_persian_text(query).strip()
    if not hits:
        return []
    query_tokens = tokenize_lexical(normalized_query)
    query_numbers = set(_NUMBER_RE.findall(normalized_query))
    query_has_browser = bool(_BROWSER_RE.search(normalized_query))
    query_phrases = _query_phrases(normalized_query)

    boosted: list[tuple[float, str, float]] = []
    for hit in hits:
        document = index.document(hit.chunk_id)
        if document is None:
            boosted.append((hit.score, hit.chunk_id, hit.score))
            continue
        text = normalize_persian_text(document.text)
        heading = normalize_persian_text(document.heading or "")
        multiplier = 1.0

        faq_lines = _faq_question_lines(text)
        if any(_near_exact_question(normalized_query, line) for line in faq_lines):
            multiplier *= 2.2
        elif any(_token_coverage(query_tokens, line) >= 0.75 for line in faq_lines):
            multiplier *= 1.55

        if any(phrase and phrase in text for phrase in query_phrases):
            multiplier *= 1.25
        if heading and any(phrase and phrase in heading for phrase in query_phrases):
            multiplier *= 1.15

        text_numbers = set(_NUMBER_RE.findall(text))
        if query_numbers and query_numbers & text_numbers:
            multiplier *= 1.30
        if query_has_browser and _BROWSER_RE.search(text):
            multiplier *= 1.25
        if _COURSE_CODE_RE.search(normalized_query) and _COURSE_CODE_RE.search(text):
            multiplier *= 1.20

        # Single discriminative content tokens (password, username, Chrome, …).
        content = [token for token in query_tokens if len(token) >= 3]
        if len(content) == 1 and content[0] in set(document.tokens):
            multiplier *= 1.20

        boosted.append((hit.score * multiplier, hit.chunk_id, hit.score))

    boosted.sort(key=lambda item: (-item[0], item[1]))
    return [
        BM25Hit(chunk_id=chunk_id, score=score, rank=rank)
        for rank, (score, chunk_id, _raw) in enumerate(boosted, start=1)
    ]


def fuse_dense_and_bm25(
    *,
    dense_ids: list[str],
    bm25_ids: list[str],
    dense_scores: dict[str, float],
    bm25_scores: dict[str, float],
    rrf_k: int = _RRF_K,
    limit: int = _RC32_CANDIDATE_CAP,
) -> tuple[list[str], dict[str, float], HybridDiagnostics]:
    """Fuse dense + BM25 id lists with RRF and return diagnostics."""
    fused = reciprocal_rank_fusion([dense_ids, bm25_ids], k=rrf_k)
    fused_ids = [chunk_id for chunk_id, _score in fused[: max(1, limit)]]
    rrf_scores = {chunk_id: score for chunk_id, score in fused}
    dense_top = tuple(
        RankedId(chunk_id=chunk_id, rank=rank, score=dense_scores.get(chunk_id, 0.0))
        for rank, chunk_id in enumerate(dense_ids[:10], start=1)
    )
    bm25_top = tuple(
        RankedId(chunk_id=chunk_id, rank=rank, score=bm25_scores.get(chunk_id, 0.0))
        for rank, chunk_id in enumerate(bm25_ids[:10], start=1)
    )
    rrf_top = tuple(
        RankedId(chunk_id=chunk_id, rank=rank, score=score)
        for rank, (chunk_id, score) in enumerate(fused[:10], start=1)
    )
    diagnostics = HybridDiagnostics(
        dense_top=dense_top,
        bm25_top=bm25_top,
        rrf_top=rrf_top,
        rrf_k=rrf_k,
        dense_pool=len(dense_ids),
        bm25_pool=len(bm25_ids),
    )
    return fused_ids, rrf_scores, diagnostics


def blend_cosine_with_rrf(
    *,
    cosine_score: float,
    rrf_score: float,
    max_rrf_score: float,
) -> float:
    """Keep cosine dominant while lifting strong RRF lexical matches into RC3.2 range."""
    if max_rrf_score <= 0.0:
        return max(0.0, min(1.0, cosine_score))
    rrf_norm = rrf_score / max_rrf_score
    blended = (0.72 * cosine_score) + (0.28 * rrf_norm)
    return max(0.0, min(1.0, blended))


def _ranked_to_dict(item: RankedId) -> dict[str, object]:
    return {
        "chunk_id": item.chunk_id,
        "rank": item.rank,
        "score": round(item.score, 6),
    }


def _query_phrases(query: str) -> list[str]:
    tokens = [match.group(0).casefold() for match in _TOKEN_RE.finditer(query)]
    phrases: list[str] = []
    compact = re.sub(r"\s+", " ", query.strip().casefold())
    if compact:
        phrases.append(compact)
    if len(tokens) >= 3:
        phrases.append(" ".join(tokens[:3]))
        phrases.append(" ".join(tokens[-3:]))
    if len(tokens) >= 2:
        for index in range(len(tokens) - 1):
            phrases.append(f"{tokens[index]} {tokens[index + 1]}")
    # Longest first.
    unique: list[str] = []
    seen: set[str] = set()
    for phrase in sorted(phrases, key=len, reverse=True):
        if phrase in seen or len(phrase) < 3:
            continue
        seen.add(phrase)
        unique.append(phrase)
    return unique


def _faq_question_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.endswith(("؟", "?")):
            lines.append(line)
    return lines


def _near_exact_question(query: str, line: str) -> bool:
    left = re.sub(r"[\s؟?\u200c]+", "", query.casefold())
    right = re.sub(r"[\s؟?\u200c]+", "", line.casefold())
    if not left or not right:
        return False
    return left == right or left in right or right in left


def _token_coverage(query_tokens: list[str], line: str) -> float:
    if not query_tokens:
        return 0.0
    line_tokens = set(tokenize_lexical(line))
    if not line_tokens:
        return 0.0
    hits = sum(1 for token in query_tokens if token in line_tokens)
    return hits / len(query_tokens)
