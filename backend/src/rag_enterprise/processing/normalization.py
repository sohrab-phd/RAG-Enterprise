"""Persian text normalization.

Implements Feature 002 Persian normalization rules in a fixed, deterministic order.
The pipeline is idempotent: ``normalize_persian_text(normalize_persian_text(x)) ==
normalize_persian_text(x)`` for all inputs.
"""

from __future__ import annotations

import re
import unicodedata

ARABIC_YEH = "\u064a"
PERSIAN_YEH = "\u06cc"
ARABIC_ALEF_MAKSURA = "\u0649"
ARABIC_KAF = "\u0643"
PERSIAN_KAF = "\u06a9"
TATWEEL = "\u0640"
ZWNJ = "\u200c"

# Persian + Arabic-Indic digits → Latin (Feature 002).
_DIGIT_TRANSLATION = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)

# Latin curly / smart quotes → ASCII. Persian guillemets «» are already canonical.
_QUOTE_TRANSLATION = str.maketrans(
    {
        "\u201c": '"',  # “
        "\u201d": '"',  # ”
        "\u201e": '"',  # „
        "\u201f": '"',  # ‟
        "\u2018": "'",  # ‘
        "\u2019": "'",  # ’
        "\u201a": "'",  # ‚
        "\u201b": "'",  # ‛
        "\u2032": "'",  # ′
        "\u2033": '"',  # ″
    }
)

# Office / PDF spacing artifacts → ordinary space (ZWNJ is excluded).
_UNICODE_SPACE_RE = re.compile("[\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000]")

# Arabic tashkeel / Quranic marks. Keep U+0654 HAMZA ABOVE (Persian ezafe on هٔ).
_ARABIC_DIACRITICS_RE = re.compile("[\u0610-\u061a\u064b-\u0652\u0655-\u065f\u0670\u06d6-\u06ed]")

# Collapse meaningless repeated punctuation; keep a single semantic mark.
# Ellipsis handled separately so "..." stays three dots.
_REPEATED_PUNCT_RE = re.compile(r"([؟!!?,،؛;:])\1+")
_ELLIPSIS_DOTS_RE = re.compile(r"\.{4,}")

_LETTER_CATEGORY_PREFIX = "L"


def normalize_persian_text(text: str) -> str:
    """Normalize Persian document / query surface text.

    Order (deterministic):
    1. Unicode NFC
    2. Invisible / format cleanup (keep valid ZWNJ for later)
    3. Tatweel removal
    4. Arabic diacritic removal
    5. Arabic ي/ى/ك → Persian ی/ک
    6. Persian / Arabic-Indic digits → Latin
    7. Quotation / punctuation unification
    8. Collapse meaningless repeated punctuation (preserve semantic marks)
    9. ZWNJ normalization (never drop letter–ZWNJ–letter half-spaces)
    10. Line-ending normalization (``\\r\\n`` / ``\\r`` → ``\\n``)
    11. Unicode space artifacts → ordinary space
    12. Control-char strip (keep ``\\n``; tabs collapse in whitespace pass)
    13. Whitespace normalization (preserve blank lines)
    """
    normalized = unicodedata.normalize("NFC", text)
    normalized = _remove_invisible_unicode(normalized)
    normalized = normalized.replace(TATWEEL, "")
    normalized = _ARABIC_DIACRITICS_RE.sub("", normalized)
    normalized = (
        normalized.replace(ARABIC_YEH, PERSIAN_YEH)
        .replace(ARABIC_ALEF_MAKSURA, PERSIAN_YEH)
        .replace(ARABIC_KAF, PERSIAN_KAF)
    )
    normalized = normalized.translate(_DIGIT_TRANSLATION)
    normalized = _normalize_punctuation(normalized)
    normalized = _collapse_repeated_punctuation(normalized)
    normalized = _normalize_zwnj(normalized)
    # Convert legacy line endings before Cc stripping removes bare ``\r``.
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _UNICODE_SPACE_RE.sub(" ", normalized)
    normalized = _strip_disallowed_controls(normalized)
    normalized = _cleanup_whitespace(normalized)
    return normalized


def _remove_invisible_unicode(text: str) -> str:
    """Drop zero-width / bidi / BOM artifacts while preserving ZWNJ."""
    out: list[str] = []
    for char in text:
        if char == ZWNJ:
            out.append(char)
            continue
        category = unicodedata.category(char)
        if category == "Cf":
            continue
        if char in {"\ufeff", "\u00ad"}:
            continue
        out.append(char)
    return "".join(out)


def _normalize_punctuation(text: str) -> str:
    """Unify quotes and a small set of punctuation variants."""
    normalized = text.translate(_QUOTE_TRANSLATION)
    # Fullwidth punctuation common in Office / PDF paste.
    normalized = (
        normalized.replace("\uff1f", "؟")  # ？
        .replace("\uff0c", "،")  # ，
        .replace("\uff1b", "؛")  # ；
        .replace("\u2026", "...")  # …
    )
    return normalized


def _collapse_repeated_punctuation(text: str) -> str:
    """Drop noise runs like ``!!!`` / ``؟؟``; keep one mark and ``...`` ellipsis."""
    collapsed = _REPEATED_PUNCT_RE.sub(r"\1", text)
    collapsed = _ELLIPSIS_DOTS_RE.sub("...", collapsed)
    return collapsed


def _is_letter(char: str) -> bool:
    return bool(char) and unicodedata.category(char).startswith(_LETTER_CATEGORY_PREFIX)


def _normalize_zwnj(text: str) -> str:
    """Keep morphological half-spaces; drop orphaned / duplicated ZWNJ."""
    if ZWNJ not in text:
        return text
    collapsed = re.sub(f"{ZWNJ}+", ZWNJ, text)
    out: list[str] = []
    length = len(collapsed)
    for index, char in enumerate(collapsed):
        if char != ZWNJ:
            out.append(char)
            continue
        previous = out[-1] if out else ""
        following = collapsed[index + 1] if index + 1 < length else ""
        if _is_letter(previous) and _is_letter(following):
            out.append(ZWNJ)
    return "".join(out)


def _strip_disallowed_controls(text: str) -> str:
    """Remove Cc controls except newline and tab."""
    out: list[str] = []
    for char in text:
        if char in {"\n", "\t"}:
            out.append(char)
            continue
        if unicodedata.category(char) == "Cc":
            continue
        out.append(char)
    return "".join(out)


def _cleanup_whitespace(text: str) -> str:
    lines = text.split("\n")
    cleaned_lines = [_cleanup_line_whitespace(line) for line in lines]
    return "\n".join(cleaned_lines)


def _cleanup_line_whitespace(line: str) -> str:
    parts = line.split(ZWNJ)
    cleaned_parts = [re.sub(r"[ \t]+", " ", part).strip() for part in parts]
    return ZWNJ.join(cleaned_parts)
