"""Language detection for extracted text."""

from __future__ import annotations

from lingua import Language, LanguageDetectorBuilder

_DETECTOR = (
    LanguageDetectorBuilder.from_languages(Language.PERSIAN, Language.ENGLISH)
    .with_minimum_relative_distance(0.1)
    .build()
)

MIN_TEXT_LENGTH = 20


def detect_language(text: str) -> str:
    """Return fa, en, or unknown."""
    sample = text.strip()
    if len(sample) < MIN_TEXT_LENGTH:
        return "unknown"

    detected = _DETECTOR.detect_language_of(sample[:10_000])
    if detected == Language.PERSIAN:
        return "fa"
    if detected == Language.ENGLISH:
        return "en"
    return "unknown"
