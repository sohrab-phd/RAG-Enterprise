"""Persian normalization tests."""

from rag_enterprise.processing.normalization import normalize_persian_text


def test_normalizes_arabic_yeh_and_kaf() -> None:
    text = "علي كتاب"
    result = normalize_persian_text(text)
    assert result == "علی کتاب"


def test_preserves_zwnj() -> None:
    text = "می‌خواهم"
    result = normalize_persian_text(text)
    assert "\u200c" in result
    assert result == "می‌خواهم"


def test_preserves_paragraph_breaks() -> None:
    text = "بند اول\n\nبند دوم"
    result = normalize_persian_text(text)
    assert result == "بند اول\n\nبند دوم"


def test_collapses_inline_whitespace() -> None:
    text = "سلام    دنیا"
    result = normalize_persian_text(text)
    assert result == "سلام دنیا"
