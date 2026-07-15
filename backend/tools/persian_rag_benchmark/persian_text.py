"""Persian NLP helpers used only by the diagnostics tool."""

from __future__ import annotations

import re
import unicodedata

from rag_enterprise.processing.normalization import (
    ARABIC_KAF,
    ARABIC_YEH,
    PERSIAN_KAF,
    PERSIAN_YEH,
    ZWNJ,
    normalize_persian_text,
)

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
LATIN_DIGITS = "0123456789"

_DIGIT_TO_LATIN = str.maketrans(
    PERSIAN_DIGITS + ARABIC_INDIC_DIGITS,
    LATIN_DIGITS + LATIN_DIGITS,
)
_DIGIT_TO_PERSIAN = str.maketrans(LATIN_DIGITS, PERSIAN_DIGITS)
_DIGIT_TO_ARABIC_INDIC = str.maketrans(LATIN_DIGITS, ARABIC_INDIC_DIGITS)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?؟。\n])\s+|\n{2,}")
_NUMBER = re.compile(rf"(?:[{PERSIAN_DIGITS}{ARABIC_INDIC_DIGITS}{LATIN_DIGITS}][٬,]?)+")
_PERSIAN_PUNCT = re.compile(r"[،؛؟«»]")
_ARABIC_LETTERS = re.compile(rf"[{ARABIC_YEH}{ARABIC_KAF}]")
_HALFSPACE_WORD = re.compile(rf"\S*{ZWNJ}\S*")


def to_latin_digits(text: str) -> str:
    return text.translate(_DIGIT_TO_LATIN)


def to_persian_digits(text: str) -> str:
    return to_latin_digits(text).translate(_DIGIT_TO_PERSIAN)


def to_arabic_indic_digits(text: str) -> str:
    return to_latin_digits(text).translate(_DIGIT_TO_ARABIC_INDIC)


def split_persian_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in _SENTENCE_SPLIT.split(text) if part and part.strip()]
    if parts:
        return parts
    stripped = text.strip()
    return [stripped] if stripped else []


def extract_numbers(text: str) -> list[str]:
    return _NUMBER.findall(text)


def extract_keywords(text: str, *, limit: int = 8) -> list[str]:
    tokens = re.findall(r"[\u0600-\u06FF\u200c]{2,}", text)
    stop = {
        "است",
        "هست",
        "می‌شود",
        "شود",
        "برای",
        "این",
        "آن",
        "که",
        "از",
        "در",
        "به",
        "با",
        "یا",
        "و",
        "تا",
        "یک",
        "را",
    }
    seen: list[str] = []
    for token in tokens:
        cleaned = token.strip()
        if cleaned in stop or cleaned in seen:
            continue
        seen.append(cleaned)
        if len(seen) >= limit:
            break
    return seen


def arabic_yeh_kaf_variant(text: str) -> str:
    return text.replace(PERSIAN_YEH, ARABIC_YEH).replace(PERSIAN_KAF, ARABIC_KAF)


def remove_halfspaces(text: str) -> str:
    return text.replace(ZWNJ, "")


def insert_halfspaces_naive(text: str) -> str:
    # Prefer attaching ZWNJ before common Persian suffixes when spaced.
    return re.sub(r"\s+(های|ها|ای|ام|ات)\b", rf"{ZWNJ}\1", text)


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_persian_punctuation(text: str) -> str:
    return _PERSIAN_PUNCT.sub("", text).replace(".", "").strip()


def add_noisy_punctuation(text: str) -> str:
    base = text.rstrip("؟.?!")
    return f"{base}؟؟!!"


def diagnose_language_surface(text: str) -> list[str]:
    """Return language-surface issues relative to production normalize_persian_text."""
    issues: list[str] = []
    if text != unicodedata.normalize("NFC", text):
        issues.append("not_nfc")
    if text != unicodedata.normalize("NFKC", text):
        issues.append("needs_nfkc")
    if _ARABIC_LETTERS.search(text):
        issues.append("arabic_yeh_or_kaf")
    if "  " in text or "\t" in text:
        issues.append("whitespace")
    if any(ch in text for ch in ARABIC_INDIC_DIGITS):
        issues.append("arabic_indic_digits")
    if any(ch in text for ch in PERSIAN_DIGITS) and any(ch in text for ch in LATIN_DIGITS):
        issues.append("mixed_digits")
    normalized = normalize_persian_text(text)
    if normalized != text:
        issues.append("differs_from_production_normalize")
    return issues


def token_estimate(text: str) -> int:
    # Approximate: whitespace + ZWNJ-aware Persian tokens.
    return max(1, len(re.findall(r"\S+", text)))


def looks_like_list(text: str) -> bool:
    return bool(re.search(r"(^|\n)\s*([0-9۰-۹]+[\.\)-]|[-•▪])\s+", text))


def looks_like_table(text: str) -> bool:
    pipes = text.count("|")
    tabs = text.count("\t")
    return pipes >= 3 or tabs >= 3
