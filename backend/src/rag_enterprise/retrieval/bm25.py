"""Okapi BM25 lexical retrieval (Python-only, no external search service)."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from rag_enterprise.processing.normalization import normalize_persian_text

# Shared with RC3.2 ranking character class, plus ZWNJ so نیم‌فاصله compounds
# like «پیش‌نیاز» stay one token and match «پیشنیاز».
_TOKEN_RE = re.compile(r"[\w\u0600-\u06FF\u200c]+", re.UNICODE)

_DEFAULT_K1 = 1.5
_DEFAULT_B = 0.75


@dataclass(frozen=True)
class LexicalDocument:
    """One indexed chunk prepared for BM25."""

    chunk_id: str
    document_id: str
    document_version_id: str
    knowledge_base_id: str
    chunk_index: int
    start_char: int
    end_char: int
    heading: str | None
    language: str | None
    text: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class BM25Hit:
    """Ranked BM25 match."""

    chunk_id: str
    score: float
    rank: int


def tokenize_lexical(text: str) -> list[str]:
    """Tokenize after the shared Persian normalization pipeline."""
    normalized = normalize_persian_text(text or "").strip()
    if not normalized:
        return []
    tokens: list[str] = []
    for match in _TOKEN_RE.finditer(normalized):
        token = match.group(0).replace("\u200c", "").casefold()
        token = token.strip("؟?")
        if token:
            tokens.append(token)
    return tokens


def split_faq_segments(text: str) -> list[str]:
    """Split multi-FAQ chunks into question-led segments for sharper BM25 matching."""
    normalized = normalize_persian_text(text or "").strip()
    if not normalized:
        return []
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    if not lines:
        return [normalized]

    segments: list[str] = []
    current: list[str] = []
    for line in lines:
        is_question = line.endswith(("؟", "?"))
        if is_question and current:
            segments.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        segments.append("\n".join(current))

    # Keep whole text as a fallback segment so non-FAQ prose still matches.
    if len(segments) > 1:
        segments.append(normalized)
    return segments


class BM25Index:
    """In-memory Okapi BM25 index over lexical documents."""

    def __init__(
        self,
        documents: list[LexicalDocument],
        *,
        k1: float = _DEFAULT_K1,
        b: float = _DEFAULT_B,
    ) -> None:
        expanded: list[LexicalDocument] = []
        for document in documents:
            source = f"{document.heading}\n{document.text}" if document.heading else document.text
            segments = split_faq_segments(source)
            for segment in segments:
                tokens = tuple(tokenize_lexical(segment))
                if not tokens:
                    continue
                expanded.append(
                    LexicalDocument(
                        chunk_id=document.chunk_id,
                        document_id=document.document_id,
                        document_version_id=document.document_version_id,
                        knowledge_base_id=document.knowledge_base_id,
                        chunk_index=document.chunk_index,
                        start_char=document.start_char,
                        end_char=document.end_char,
                        heading=document.heading,
                        language=document.language,
                        text=document.text,
                        tokens=tokens,
                    )
                )
            if not any(item.chunk_id == document.chunk_id for item in expanded):
                expanded.append(document)

        self._documents = expanded
        self._canonical = {document.chunk_id: document for document in documents}
        self._k1 = k1
        self._b = b
        self._doc_len = [len(document.tokens) for document in self._documents]
        self._avgdl = sum(self._doc_len) / len(self._doc_len) if self._doc_len else 0.0
        self._df: dict[str, int] = {}
        for document in self._documents:
            for token in set(document.tokens):
                self._df[token] = self._df.get(token, 0) + 1

    @property
    def size(self) -> int:
        # IDF uses segment corpus size; report canonical chunk count for diagnostics.
        return len(self._documents)

    @property
    def chunk_count(self) -> int:
        return len(self._canonical)

    def document(self, chunk_id: str) -> LexicalDocument | None:
        return self._canonical.get(chunk_id)

    def search(self, query_tokens: list[str], *, top_k: int) -> list[BM25Hit]:
        """Return top_k chunk ids by max BM25 score across FAQ segments."""
        if not self._documents or not query_tokens or top_k <= 0:
            return []

        best: dict[str, tuple[float, int]] = {}
        for index, document in enumerate(self._documents):
            score = self._score_document(query_tokens, index)
            if score <= 0.0:
                continue
            previous = best.get(document.chunk_id)
            if previous is None or score > previous[0]:
                best[document.chunk_id] = (score, document.chunk_index)

        scored = [(score, chunk_id, chunk_index) for chunk_id, (score, chunk_index) in best.items()]
        scored.sort(key=lambda item: (-item[0], item[1], item[2]))
        return [
            BM25Hit(chunk_id=chunk_id, score=score, rank=rank)
            for rank, (score, chunk_id, _chunk_index) in enumerate(scored[:top_k], start=1)
        ]

    def _score_document(self, query_tokens: list[str], doc_index: int) -> float:
        document = self._documents[doc_index]
        if not document.tokens:
            return 0.0
        tf: dict[str, int] = {}
        for token in document.tokens:
            tf[token] = tf.get(token, 0) + 1
        score = 0.0
        doc_len = self._doc_len[doc_index]
        for token in query_tokens:
            frequency = tf.get(token)
            if not frequency:
                continue
            df = self._df.get(token, 0)
            idf = math.log(1.0 + (self.size - df + 0.5) / (df + 0.5))
            denominator = frequency + self._k1 * (
                1.0 - self._b + self._b * doc_len / max(self._avgdl, 1e-9)
            )
            score += idf * (frequency * (self._k1 + 1.0)) / denominator
        return score
