"""Persian text normalization."""

from __future__ import annotations

import re
import unicodedata

ARABIC_YEH = "\u064a"
PERSIAN_YEH = "\u06cc"
ARABIC_KAF = "\u0643"
PERSIAN_KAF = "\u06a9"
ZWNJ = "\u200c"


def normalize_persian_text(text: str) -> str:
    """Apply NFC, Persian letter mapping, and whitespace cleanup."""
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace(ARABIC_YEH, PERSIAN_YEH).replace(ARABIC_KAF, PERSIAN_KAF)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _cleanup_whitespace(normalized)
    return normalized


def _cleanup_whitespace(text: str) -> str:
    lines = text.split("\n")
    cleaned_lines: list[str] = []
    for line in lines:
        cleaned_lines.append(_cleanup_line_whitespace(line))
    return "\n".join(cleaned_lines)


def _cleanup_line_whitespace(line: str) -> str:
    parts = line.split(ZWNJ)
    cleaned_parts = [re.sub(r"[ \t]+", " ", part).strip() for part in parts]
    return ZWNJ.join(cleaned_parts)
