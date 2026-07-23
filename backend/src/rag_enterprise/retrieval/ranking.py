"""Deterministic dense-retrieval ranking calibration for Persian FAQ chunks.

Applies small lexical / FAQ-structure bonuses on top of cosine similarity so that
near-tied hybrid neighbors order correctly (Hit@1 / MRR). Hybrid retrieval
(dense + BM25 + RRF) feeds this module; RC3.2 remains the final ranking stage.

The adjusted score is written back to ``RetrievedChunk.score`` so downstream
context assembly (which sorts by score) preserves ranking order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rag_enterprise.processing.normalization import normalize_persian_text
from rag_enterprise.retrieval.models import RetrievedChunk

# Keep deltas modest so weak cosine matches cannot leapfrog strong ones.
_MAX_TOTAL_BONUS = 0.18
_MAX_TOTAL_PENALTY = 0.10

_W_FAQ_QUESTION = 0.12
_W_HEADING = 0.06
_W_PHRASE = 0.10
_W_BODY_OVERLAP = 0.06
_W_GENERIC_PENALTY = 0.05
_W_DISTRACTOR_PENALTY = 0.06

_TOKEN_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)
_QUESTION_MARK_RE = re.compile(r"[؟?]")

# High-frequency Persian function words + weak FAQ scaffolding.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "و",
        "در",
        "از",
        "به",
        "که",
        "این",
        "آن",
        "را",
        "با",
        "برای",
        "تا",
        "یا",
        "هم",
        "اگر",
        "یک",
        "ها",
        "های",
        "است",
        "هست",
        "بود",
        "شد",
        "می",
        "نمی",
        "شود",
        "شودد",
        "کنیم",
        "شودید",
        "چه",
        "چیست",
        "چگونه",
        "کدام",
        "چرا",
        "آیا",
        "کی",
        "کجا",
        "the",
        "a",
        "an",
        "is",
        "are",
        "of",
        "to",
        "in",
        "for",
        "and",
        "or",
        "on",
    }
)

# Tokens that often pull the wrong FAQ neighbor when they dominate overlap.
_DISTRACTOR_PAIRS: tuple[tuple[frozenset[str], frozenset[str]], ...] = (
    (
        frozenset({"اولیه", "اوليه", "پیشفرض", "پيشفرض"}),
        frozenset({"فراموشی", "فراموش", "ریست", "بازیابی"}),
    ),
    (frozenset({"ورود", "وارد"}), frozenset({"خروج", "فراموشی", "ریست"})),
    (frozenset({"نام", "کاربری", "شناسه"}), frozenset({"فراموشی", "ریست", "رمز"})),
)


@dataclass(frozen=True)
class RankingBreakdown:
    """Explainable ranking components for one candidate."""

    chunk_id: str
    cosine_score: float
    adjusted_score: float
    bonuses: dict[str, float] = field(default_factory=dict)
    penalties: dict[str, float] = field(default_factory=dict)
    best_faq_question: str | None = None
    reasons_won: tuple[str, ...] = ()
    reasons_lost: tuple[str, ...] = ()


@dataclass(frozen=True)
class RankingDiagnostics:
    """Per-query ranking explanation (top candidates)."""

    query: str
    candidate_count: int
    returned_count: int
    rankings: tuple[RankingBreakdown, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "query": self.query,
            "candidate_count": self.candidate_count,
            "returned_count": self.returned_count,
            "rankings": [
                {
                    "rank": index + 1,
                    "chunk_id": item.chunk_id,
                    "cosine_score": round(item.cosine_score, 6),
                    "adjusted_score": round(item.adjusted_score, 6),
                    "bonuses": {key: round(value, 6) for key, value in item.bonuses.items()},
                    "penalties": {key: round(value, 6) for key, value in item.penalties.items()},
                    "best_faq_question": item.best_faq_question,
                    "reasons_won": list(item.reasons_won),
                    "reasons_lost": list(item.reasons_lost),
                }
                for index, item in enumerate(self.rankings)
            ],
        }


def candidate_pool_size(top_k: int, *, max_top_k: int = 50) -> int:
    """Fetch a slightly larger dense pool, then re-rank and truncate to top_k."""
    pooled = max(top_k, min(max_top_k, max(top_k * 2, top_k + 8)))
    return pooled


def rank_dense_hits(
    *,
    query: str,
    chunks: list[RetrievedChunk],
    top_k: int,
) -> tuple[list[RetrievedChunk], RankingDiagnostics]:
    """Re-rank cosine hits with deterministic Persian FAQ lexical calibration."""
    normalized_query = normalize_persian_text(query).strip()
    if not chunks:
        empty = RankingDiagnostics(
            query=normalized_query,
            candidate_count=0,
            returned_count=0,
            rankings=(),
        )
        return [], empty

    scored: list[tuple[RetrievedChunk, RankingBreakdown, float]] = []
    for chunk in chunks:
        breakdown = _score_chunk(normalized_query, chunk)
        scored.append((chunk, breakdown, breakdown.adjusted_score))

    scored.sort(
        key=lambda item: (
            -item[2],
            -item[1].cosine_score,
            str(item[0].document_id),
            item[0].chunk_index,
            str(item[0].chunk_id),
        )
    )

    trimmed = scored[: max(1, top_k)]
    reranked: list[RetrievedChunk] = []
    breakdowns: list[RankingBreakdown] = []
    for chunk, breakdown, _adjusted in trimmed:
        reranked.append(chunk.model_copy(update={"score": breakdown.adjusted_score}))
        breakdowns.append(breakdown)

    # Annotate win/loss reasons relative to neighbors.
    annotated = _annotate_relative_reasons(tuple(breakdowns))
    diagnostics = RankingDiagnostics(
        query=normalized_query,
        candidate_count=len(chunks),
        returned_count=len(reranked),
        rankings=annotated,
    )
    return reranked, diagnostics


def _score_chunk(query: str, chunk: RetrievedChunk) -> RankingBreakdown:
    cosine = float(chunk.score)
    text = normalize_persian_text(chunk.text or "")
    heading = normalize_persian_text(chunk.heading or "")
    query_tokens = _content_tokens(query)
    query_all = _all_tokens(query)

    bonuses: dict[str, float] = {}
    penalties: dict[str, float] = {}

    faq_lines = _extract_question_lines(text)
    best_faq: str | None = None
    best_faq_overlap = 0.0
    for line in faq_lines:
        overlap = _jaccard(_content_tokens(line), query_tokens)
        if overlap > best_faq_overlap:
            best_faq_overlap = overlap
            best_faq = line
    if best_faq_overlap > 0.0:
        bonuses["faq_question_overlap"] = _W_FAQ_QUESTION * best_faq_overlap

    if heading:
        heading_overlap = _jaccard(_content_tokens(heading), query_tokens)
        if heading_overlap > 0.0:
            bonuses["heading_overlap"] = _W_HEADING * heading_overlap

    phrase_targets = [best_faq or "", heading, text]
    phrase_hit = False
    # Prefer longer contiguous query substrings (3+ tokens) then bigrams.
    phrases = _candidate_phrases(query)
    for phrase in phrases:
        if len(phrase) < 4:
            continue
        if any(phrase in target for target in phrase_targets if target):
            bonuses["exact_phrase"] = _W_PHRASE
            phrase_hit = True
            break
    if not phrase_hit and len(query_tokens) >= 2:
        # Soft bigram presence in FAQ line.
        bigrams = _token_bigrams(query_all)
        faq_blob = best_faq or ""
        hits = sum(1 for gram in bigrams if gram in faq_blob)
        if bigrams and hits:
            bonuses["bigram_faq"] = _W_PHRASE * 0.5 * (hits / len(bigrams))

    body_overlap = _jaccard(_content_tokens(text), query_tokens)
    if body_overlap > 0.0:
        bonuses["body_token_overlap"] = _W_BODY_OVERLAP * body_overlap

    # Penalty: overlap is only stopwords / empty content tokens.
    if (
        query_tokens
        and not (_content_tokens(text) & query_tokens)
        and not best_faq_overlap
        and set(_all_tokens(text)) & set(_all_tokens(query))
    ):
        penalties["generic_only_overlap"] = _W_GENERIC_PENALTY

    distractor = _distractor_penalty(query_tokens, _content_tokens(text), best_faq)
    if distractor > 0.0:
        penalties["distractor_faq"] = distractor

    bonus_total = min(_MAX_TOTAL_BONUS, sum(bonuses.values()))
    penalty_total = min(_MAX_TOTAL_PENALTY, sum(penalties.values()))
    adjusted = max(0.0, min(1.0, cosine + bonus_total - penalty_total))

    return RankingBreakdown(
        chunk_id=str(chunk.chunk_id),
        cosine_score=cosine,
        adjusted_score=adjusted,
        bonuses=bonuses,
        penalties=penalties,
        best_faq_question=best_faq,
    )


def _annotate_relative_reasons(
    rankings: tuple[RankingBreakdown, ...],
) -> tuple[RankingBreakdown, ...]:
    if not rankings:
        return ()
    leader = rankings[0]
    annotated: list[RankingBreakdown] = []
    for index, item in enumerate(rankings):
        won: list[str] = []
        lost: list[str] = []
        if index == 0:
            if item.bonuses:
                top_bonus = max(item.bonuses.items(), key=lambda pair: pair[1])
                won.append(f"highest_adjusted_score; top_bonus={top_bonus[0]}:{top_bonus[1]:.3f}")
            else:
                won.append("highest_adjusted_score; cosine_led")
            if item.best_faq_question:
                won.append(f"best_faq_line={item.best_faq_question[:80]}")
        else:
            delta = leader.adjusted_score - item.adjusted_score
            lost.append(f"behind_rank1_by={delta:.3f}")
            missing = [
                key
                for key, value in leader.bonuses.items()
                if value > item.bonuses.get(key, 0.0) + 0.01
            ]
            if missing:
                lost.append("weaker_bonuses=" + ",".join(missing))
            if item.penalties:
                top_pen = max(item.penalties.items(), key=lambda pair: pair[1])
                lost.append(f"penalty={top_pen[0]}:{top_pen[1]:.3f}")
        annotated.append(
            RankingBreakdown(
                chunk_id=item.chunk_id,
                cosine_score=item.cosine_score,
                adjusted_score=item.adjusted_score,
                bonuses=item.bonuses,
                penalties=item.penalties,
                best_faq_question=item.best_faq_question,
                reasons_won=tuple(won),
                reasons_lost=tuple(lost),
            )
        )
    return tuple(annotated)


def _extract_question_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.endswith("؟") or line.endswith("?"):
            lines.append(line)
            continue
        # Multi-sentence lines: keep each question-bearing segment.
        parts = _QUESTION_MARK_RE.split(line)
        marks = _QUESTION_MARK_RE.findall(line)
        for index, part in enumerate(parts[:-1]):
            segment = (part.strip() + marks[index]).strip()
            if len(segment) >= 8:
                lines.append(segment)
    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for line in lines:
        key = line.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(line)
    return unique


def _candidate_phrases(query: str) -> list[str]:
    compact = re.sub(r"\s+", " ", query.strip())
    tokens = _all_tokens(compact)
    phrases: list[str] = []
    if len(tokens) >= 3:
        phrases.append(" ".join(tokens[:3]))
        phrases.append(" ".join(tokens[-3:]))
    if len(tokens) >= 2:
        for index in range(len(tokens) - 1):
            phrases.append(f"{tokens[index]} {tokens[index + 1]}")
    # Longest first for matching priority.
    phrases.sort(key=len, reverse=True)
    return phrases


def _token_bigrams(tokens: list[str]) -> list[str]:
    return [f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1)]


def _distractor_penalty(
    query_tokens: set[str],
    text_tokens: set[str],
    best_faq: str | None,
) -> float:
    faq_tokens = _content_tokens(best_faq or "")
    for target, distractors in _DISTRACTOR_PAIRS:
        if not (query_tokens & target):
            continue
        # Query wants the target sense; chunk leans on distractor FAQ.
        if (text_tokens & distractors or faq_tokens & distractors) and not (
            faq_tokens & target or text_tokens & target
        ):
            return _W_DISTRACTOR_PENALTY
    return 0.0


def _all_tokens(text: str) -> list[str]:
    return [match.group(0).casefold() for match in _TOKEN_RE.finditer(text)]


def _content_tokens(text: str) -> set[str]:
    return {token for token in _all_tokens(text) if token not in _STOPWORDS and len(token) > 1}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    intersection = len(left & right)
    union = len(left | right)
    return intersection / union if union else 0.0
