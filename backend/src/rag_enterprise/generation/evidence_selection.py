"""Deterministic evidence selection between retrieval and PromptBuilder.

RC3.6 V1: heuristic scoring only — no ML, cross-encoder, or LLM judge.
Filters ranked retrieval hits into PRIMARY / SUPPLEMENTARY / IRRELEVANT and
passes a small evidence set to PromptBuilder.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from rag_enterprise.processing.normalization import normalize_persian_text
from rag_enterprise.retrieval.models import RetrievedChunk

_TOKEN_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)
_PERSIAN_RE = re.compile(r"[\u0600-\u06FF]")
_NUMBER_RE = re.compile(
    r"(?<![\w\u0600-\u06FF])("
    r"\d{1,4}"
    r"|[۰-۹]{1,4}"
    r")(?![\w\u0600-\u06FF])"
)
_QUESTION_MARK_RE = re.compile(r"[؟?]")
_ARABIC_INDIC = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

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
        "کند",
        "کنیم",
        "کنید",
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

# Query sense → distractor sense (drop wrong FAQ neighbors).
_DISTRACTOR_PAIRS: tuple[tuple[frozenset[str], frozenset[str]], ...] = (
    (
        frozenset({"اولیه", "اوليه", "پیشفرض", "پيشفرض"}),
        frozenset({"فراموشی", "فراموش", "ریست", "بازیابی"}),
    ),
    (frozenset({"ورود", "وارد"}), frozenset({"خروج", "فراموشی", "ریست"})),
    (frozenset({"نام", "کاربری", "شناسه"}), frozenset({"فراموشی", "ریست"})),
    (frozenset({"پیشنیاز", "پیش‌نیاز", "پيشنياز"}), frozenset({"همنیاز", "هم‌نیاز", "همنياز"})),
    (frozenset({"همنیاز", "هم‌نیاز", "همنياز"}), frozenset({"پیشنیاز", "پیش‌نیاز", "پيشنياز"})),
    (
        frozenset({"اضطراری", "اضطراري"}),
        frozenset({"اضافه", "حذف‌واضافه", "حذفواضافه"}),
    ),
)

_MAX_PRIMARY = 3
_MAX_SUPPLEMENTARY = 2
_PRIMARY_THRESHOLD = 0.42
_SUPPLEMENTARY_THRESHOLD = 0.28
_IRRELEVANT_HARD_MAX = 0.18

# Signal weights (sum ≈ 1.0 before penalties).
_W_LEXICAL = 0.14
_W_PERSIAN_KW = 0.12
_W_HEADING = 0.10
_W_FAQ = 0.16
_W_PHRASE = 0.12
_W_NUMERIC = 0.08
_W_ENTITY = 0.06
_W_SECTION = 0.05
_W_RC32 = 0.10
_W_HYBRID_RANK = 0.07


class EvidenceLabel(StrEnum):
    """Evidence role relative to the user question."""

    PRIMARY = "PRIMARY"
    SUPPLEMENTARY = "SUPPLEMENTARY"
    IRRELEVANT = "IRRELEVANT"


@dataclass(frozen=True)
class EvidenceSignals:
    """Per-chunk deterministic evidence signal vector."""

    lexical_overlap: float
    persian_keyword_overlap: float
    heading_similarity: float
    faq_question_similarity: float
    exact_phrase: float
    numeric_agreement: float
    named_entities: float
    section_proximity: float
    rc32_ranking_score: float
    hybrid_rank_score: float

    def to_dict(self) -> dict[str, float]:
        return {
            "lexical_overlap": round(self.lexical_overlap, 6),
            "persian_keyword_overlap": round(self.persian_keyword_overlap, 6),
            "heading_similarity": round(self.heading_similarity, 6),
            "faq_question_similarity": round(self.faq_question_similarity, 6),
            "exact_phrase": round(self.exact_phrase, 6),
            "numeric_agreement": round(self.numeric_agreement, 6),
            "named_entities": round(self.named_entities, 6),
            "section_proximity": round(self.section_proximity, 6),
            "rc32_ranking_score": round(self.rc32_ranking_score, 6),
            "hybrid_rank_score": round(self.hybrid_rank_score, 6),
        }


@dataclass(frozen=True)
class ScoredEvidence:
    """One retrieved chunk after evidence scoring."""

    chunk: RetrievedChunk
    label: EvidenceLabel
    selection_score: float
    selection_reason: str
    signals: EvidenceSignals
    retrieval_rank: int


@dataclass(frozen=True)
class EvidenceSelectionResult:
    """Selected evidence set plus diagnostics for PromptBuilder / eval."""

    query: str
    primary: tuple[RetrievedChunk, ...]
    supplementary: tuple[RetrievedChunk, ...]
    discarded: tuple[RetrievedChunk, ...]
    scored: tuple[ScoredEvidence, ...]
    conflict: bool
    conflict_reason: str | None = None
    selection_latency_ms: float = 0.0

    @property
    def chunks_for_prompt(self) -> list[RetrievedChunk]:
        """PRIMARY then SUPPLEMENTARY — never IRRELEVANT."""
        return [*self.primary, *self.supplementary]

    @property
    def selected_primary_ids(self) -> list[str]:
        return [str(chunk.chunk_id) for chunk in self.primary]

    @property
    def selected_support_ids(self) -> list[str]:
        return [str(chunk.chunk_id) for chunk in self.supplementary]

    @property
    def discarded_ids(self) -> list[str]:
        return [str(chunk.chunk_id) for chunk in self.discarded]

    def to_diagnostics(self) -> dict[str, object]:
        scored_by_id = {item.chunk.chunk_id: item for item in self.scored}
        return {
            "query": self.query,
            "conflict": self.conflict,
            "conflict_reason": self.conflict_reason,
            "selection_latency_ms": round(self.selection_latency_ms, 3),
            "selected_primary": self.selected_primary_ids,
            "selected_support": self.selected_support_ids,
            "discarded": self.discarded_ids,
            "average_selected_chunks": len(self.chunks_for_prompt),
            "average_discarded_chunks": len(self.discarded),
            "candidates": [
                {
                    "chunk_id": str(item.chunk.chunk_id),
                    "retrieval_rank": item.retrieval_rank,
                    "label": item.label.value,
                    "selection_score": round(item.selection_score, 6),
                    "selection_reason": item.selection_reason,
                    "signals": item.signals.to_dict(),
                    "heading": item.chunk.heading,
                    "text_preview": (item.chunk.text or "")[:180],
                }
                for item in self.scored
            ],
            "prompt_chunk_ids": [str(chunk.chunk_id) for chunk in self.chunks_for_prompt],
            "prompt_char_estimate": sum(len(chunk.text or "") for chunk in self.chunks_for_prompt),
            "original_char_estimate": sum(
                len(scored_by_id[chunk_id].chunk.text or "") for chunk_id in scored_by_id
            ),
        }


@dataclass
class _WorkingScore:
    chunk: RetrievedChunk
    retrieval_rank: int
    signals: EvidenceSignals
    selection_score: float
    label: EvidenceLabel = EvidenceLabel.IRRELEVANT
    selection_reason: str = "irrelevant"
    bonuses: dict[str, float] = field(default_factory=dict)
    penalties: dict[str, float] = field(default_factory=dict)


def select_evidence(
    *,
    question: str,
    chunks: list[RetrievedChunk],
    max_primary: int = _MAX_PRIMARY,
    max_supplementary: int = _MAX_SUPPLEMENTARY,
) -> EvidenceSelectionResult:
    """Score ranked retrieval hits and return the prompt evidence set."""
    import time

    started = time.perf_counter()
    query = normalize_persian_text(question).strip()
    if not chunks:
        return EvidenceSelectionResult(
            query=query,
            primary=(),
            supplementary=(),
            discarded=(),
            scored=(),
            conflict=False,
            selection_latency_ms=(time.perf_counter() - started) * 1000,
        )

    query_tokens = _content_tokens(query)
    query_persian = _persian_keywords(query)
    query_entities = _named_entities(query)
    query_numbers = _extract_numbers(query)
    max_rc32 = max((float(chunk.score) for chunk in chunks), default=1.0) or 1.0

    working: list[_WorkingScore] = []
    for index, chunk in enumerate(chunks, start=1):
        text = normalize_persian_text(chunk.text or "")
        heading = normalize_persian_text(chunk.heading or "")
        faq_lines = _extract_question_lines(text)
        best_faq_sim, best_faq = _best_faq_similarity(query_tokens, faq_lines)

        lexical = _jaccard(query_tokens, _content_tokens(text))
        persian_kw = _jaccard(query_persian, _persian_keywords(f"{heading}\n{text}"))
        heading_sim = _jaccard(query_tokens, _content_tokens(heading)) if heading else 0.0
        phrase = _exact_phrase_score(query, [best_faq or "", heading, text])
        numeric = _numeric_agreement(query_numbers, _extract_numbers(text))
        entities = _jaccard(query_entities, _named_entities(f"{heading}\n{text}"))
        rc32 = max(0.0, min(1.0, float(chunk.score) / max_rc32))
        hybrid_rank = 1.0 / (1.0 + (index - 1))

        signals = EvidenceSignals(
            lexical_overlap=lexical,
            persian_keyword_overlap=persian_kw,
            heading_similarity=heading_sim,
            faq_question_similarity=best_faq_sim,
            exact_phrase=phrase,
            numeric_agreement=numeric,
            named_entities=entities,
            section_proximity=0.0,  # filled after provisional ranking
            rc32_ranking_score=rc32,
            hybrid_rank_score=hybrid_rank,
        )
        penalties = _distractor_penalties(query_tokens, text, best_faq)
        score = _combine_score(signals, penalties)
        working.append(
            _WorkingScore(
                chunk=chunk,
                retrieval_rank=index,
                signals=signals,
                selection_score=score,
                penalties=penalties,
            )
        )

    # Section proximity relative to the current best candidate (same doc / near index).
    anchor = max(working, key=lambda item: item.selection_score)
    for item in working:
        proximity = _section_proximity(anchor.chunk, item.chunk)
        item.signals = EvidenceSignals(
            lexical_overlap=item.signals.lexical_overlap,
            persian_keyword_overlap=item.signals.persian_keyword_overlap,
            heading_similarity=item.signals.heading_similarity,
            faq_question_similarity=item.signals.faq_question_similarity,
            exact_phrase=item.signals.exact_phrase,
            numeric_agreement=item.signals.numeric_agreement,
            named_entities=item.signals.named_entities,
            section_proximity=proximity,
            rc32_ranking_score=item.signals.rc32_ranking_score,
            hybrid_rank_score=item.signals.hybrid_rank_score,
        )
        item.selection_score = _combine_score(item.signals, item.penalties)

    for item in working:
        item.label, item.selection_reason = _classify(item)

    primary_candidates = sorted(
        [item for item in working if item.label == EvidenceLabel.PRIMARY],
        key=lambda item: (-item.selection_score, item.retrieval_rank),
    )
    support_candidates = sorted(
        [item for item in working if item.label == EvidenceLabel.SUPPLEMENTARY],
        key=lambda item: (-item.selection_score, item.retrieval_rank),
    )

    # Guarantee at least one PRIMARY when any evidence exists above hard floor.
    if not primary_candidates:
        fallback = max(working, key=lambda item: (item.selection_score, -item.retrieval_rank))
        if fallback.selection_score >= _IRRELEVANT_HARD_MAX:
            fallback.label = EvidenceLabel.PRIMARY
            fallback.selection_reason = "promoted_best_available"
            primary_candidates = [fallback]
            support_candidates = [
                item
                for item in support_candidates
                if item.chunk.chunk_id != fallback.chunk.chunk_id
            ]

    selected_primary = primary_candidates[: max(1, max_primary)]
    selected_ids = {item.chunk.chunk_id for item in selected_primary}
    selected_support = [
        item for item in support_candidates if item.chunk.chunk_id not in selected_ids
    ][: max(0, max_supplementary)]
    selected_ids.update(item.chunk.chunk_id for item in selected_support)

    for item in working:
        if item.chunk.chunk_id in selected_ids:
            continue
        if item.label != EvidenceLabel.IRRELEVANT:
            item.label = EvidenceLabel.IRRELEVANT
            item.selection_reason = f"truncated_after_cap:{item.selection_reason}"

    discarded = tuple(item.chunk for item in working if item.chunk.chunk_id not in selected_ids)
    conflict, conflict_reason = _detect_conflict(query_numbers, selected_primary)

    scored = tuple(
        ScoredEvidence(
            chunk=item.chunk,
            label=item.label if item.chunk.chunk_id in selected_ids else EvidenceLabel.IRRELEVANT,
            selection_score=item.selection_score,
            selection_reason=item.selection_reason,
            signals=item.signals,
            retrieval_rank=item.retrieval_rank,
        )
        for item in sorted(working, key=lambda row: row.retrieval_rank)
    )

    return EvidenceSelectionResult(
        query=query,
        primary=tuple(item.chunk for item in selected_primary),
        supplementary=tuple(item.chunk for item in selected_support),
        discarded=discarded,
        scored=scored,
        conflict=conflict,
        conflict_reason=conflict_reason,
        selection_latency_ms=(time.perf_counter() - started) * 1000,
    )


def _combine_score(signals: EvidenceSignals, penalties: dict[str, float]) -> float:
    raw = (
        _W_LEXICAL * signals.lexical_overlap
        + _W_PERSIAN_KW * signals.persian_keyword_overlap
        + _W_HEADING * signals.heading_similarity
        + _W_FAQ * signals.faq_question_similarity
        + _W_PHRASE * signals.exact_phrase
        + _W_NUMERIC * signals.numeric_agreement
        + _W_ENTITY * signals.named_entities
        + _W_SECTION * signals.section_proximity
        + _W_RC32 * signals.rc32_ranking_score
        + _W_HYBRID_RANK * signals.hybrid_rank_score
        - sum(penalties.values())
    )
    return max(0.0, raw)


def _classify(item: _WorkingScore) -> tuple[EvidenceLabel, str]:
    signals = item.signals
    score = item.selection_score
    reasons: list[str] = []

    if item.penalties:
        reasons.append("distractor_penalty=" + ",".join(item.penalties))

    strong_direct = (
        signals.faq_question_similarity >= 0.45
        or signals.exact_phrase >= 0.75
        or (signals.numeric_agreement >= 1.0 and signals.lexical_overlap >= 0.15)
        or (signals.heading_similarity >= 0.5 and signals.lexical_overlap >= 0.2)
    )
    if score >= _PRIMARY_THRESHOLD or (strong_direct and score >= _SUPPLEMENTARY_THRESHOLD):
        if signals.faq_question_similarity >= 0.45:
            reasons.append("faq_match")
        if signals.exact_phrase >= 0.75:
            reasons.append("exact_phrase")
        if signals.numeric_agreement >= 1.0:
            reasons.append("numeric_agreement")
        if signals.heading_similarity >= 0.5:
            reasons.append("heading_match")
        if not reasons:
            reasons.append("high_evidence_score")
        return EvidenceLabel.PRIMARY, "+".join(reasons)

    if score >= _SUPPLEMENTARY_THRESHOLD:
        if signals.section_proximity > 0:
            reasons.append("section_neighbor")
        if signals.lexical_overlap >= 0.2:
            reasons.append("lexical_support")
        if signals.persian_keyword_overlap >= 0.25:
            reasons.append("persian_keywords")
        if not reasons:
            reasons.append("moderate_evidence_score")
        return EvidenceLabel.SUPPLEMENTARY, "+".join(reasons)

    reasons.append("below_threshold")
    return EvidenceLabel.IRRELEVANT, "+".join(reasons)


def _detect_conflict(
    query_numbers: set[str],
    primary: list[_WorkingScore],
) -> tuple[bool, str | None]:
    if len(primary) < 2:
        return False, None
    if query_numbers:
        number_sets = [_extract_numbers(item.chunk.text or "") for item in primary]
        nonempty = [nums for nums in number_sets if nums]
        if len(nonempty) >= 2:
            shared = set.intersection(*nonempty) if nonempty else set()
            all_nums = set.union(*nonempty)
            # Conflict when query asks for a number and primaries disagree on values.
            if (
                all_nums
                and not (query_numbers & shared)
                and len({frozenset(n) for n in nonempty}) > 1
            ):
                return True, "numeric_disagreement_among_primary"

    faq_answers: list[str] = []
    for item in primary:
        lines = _extract_question_lines(normalize_persian_text(item.chunk.text or ""))
        if not lines:
            continue
        # Take first non-question line after best FAQ as a crude answer span.
        text = normalize_persian_text(item.chunk.text or "")
        for line in text.splitlines():
            compact = line.strip()
            if compact and not compact.endswith(("؟", "?")) and len(compact) >= 8:
                faq_answers.append(compact)
                break
    if len(faq_answers) >= 2:
        left = _content_tokens(faq_answers[0])
        right = _content_tokens(faq_answers[1])
        if left and right and _jaccard(left, right) < 0.15 and not (left & right):
            return True, "primary_answer_spans_disagree"
    return False, None


def _section_proximity(anchor: RetrievedChunk, other: RetrievedChunk) -> float:
    if other.chunk_id == anchor.chunk_id:
        return 1.0
    if other.document_id != anchor.document_id:
        return 0.0
    distance = abs(other.chunk_index - anchor.chunk_index)
    if distance == 0:
        return 0.9
    if distance == 1:
        return 0.7
    if distance == 2:
        return 0.4
    if distance <= 4:
        return 0.2
    return 0.0


def _distractor_penalties(
    query_tokens: set[str],
    text: str,
    best_faq: str | None,
) -> dict[str, float]:
    text_tokens = _content_tokens(text)
    faq_tokens = _content_tokens(best_faq or "")
    penalties: dict[str, float] = {}
    for target, distractors in _DISTRACTOR_PAIRS:
        if not (query_tokens & target):
            continue
        if (text_tokens & distractors or faq_tokens & distractors) and not (
            faq_tokens & target or text_tokens & target
        ):
            penalties["distractor"] = 0.12
            break
    return penalties


def _best_faq_similarity(
    query_tokens: set[str],
    faq_lines: list[str],
) -> tuple[float, str | None]:
    best_sim = 0.0
    best_line: str | None = None
    for line in faq_lines:
        sim = _jaccard(query_tokens, _content_tokens(line))
        if sim > best_sim:
            best_sim = sim
            best_line = line
    return best_sim, best_line


def _exact_phrase_score(query: str, targets: list[str]) -> float:
    phrases = _candidate_phrases(query)
    if not phrases:
        return 0.0
    for phrase in phrases:
        if len(phrase) < 4:
            continue
        if any(phrase in target for target in targets if target):
            return 1.0
    # Soft bigram presence.
    tokens = _all_tokens(query)
    bigrams = [f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1)]
    if not bigrams:
        return 0.0
    blob = " ".join(targets)
    hits = sum(1 for gram in bigrams if gram in blob)
    return 0.5 * (hits / len(bigrams)) if hits else 0.0


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
    phrases.sort(key=len, reverse=True)
    return phrases


def _extract_question_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.endswith("؟") or line.endswith("?"):
            lines.append(line)
            continue
        parts = _QUESTION_MARK_RE.split(line)
        marks = _QUESTION_MARK_RE.findall(line)
        for index, part in enumerate(parts[:-1]):
            segment = (part.strip() + marks[index]).strip()
            if len(segment) >= 8:
                lines.append(segment)
    seen: set[str] = set()
    unique: list[str] = []
    for line in lines:
        key = line.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(line)
    return unique


def _extract_numbers(text: str) -> set[str]:
    found: set[str] = set()
    for match in _NUMBER_RE.finditer(text):
        raw = match.group(1).translate(_ARABIC_INDIC)
        found.add(str(int(raw)) if raw.isdigit() else raw)
    return found


def _numeric_agreement(query_numbers: set[str], chunk_numbers: set[str]) -> float:
    if not query_numbers:
        return 0.0
    if not chunk_numbers:
        return 0.0
    overlap = query_numbers & chunk_numbers
    return len(overlap) / len(query_numbers)


def _named_entities(text: str) -> set[str]:
    """Lightweight entity-like tokens: URLs hosts, Latin brands, long Persian tokens."""
    entities: set[str] = set()
    for token in _all_tokens(text):
        if token in _STOPWORDS:
            continue
        if "." in token or "http" in token:
            entities.add(token)
            continue
        if re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,}", token):
            entities.add(token)
            continue
        if _PERSIAN_RE.search(token) and len(token) >= 4:
            # Keep distinctive Persian content words as soft entities.
            entities.add(token)
    return entities


def _persian_keywords(text: str) -> set[str]:
    return {token for token in _content_tokens(text) if _PERSIAN_RE.search(token)}


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


def chunk_ids(chunks: list[RetrievedChunk] | tuple[RetrievedChunk, ...]) -> list[uuid.UUID]:
    """Helper for tests / diagnostics."""
    return [chunk.chunk_id for chunk in chunks]
