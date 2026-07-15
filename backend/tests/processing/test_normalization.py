"""Persian normalization tests."""

from __future__ import annotations

import unicodedata

import pytest

from rag_enterprise.processing.normalization import ZWNJ, normalize_persian_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("علي كتاب", "علی کتاب"),
        ("يك", "یک"),
        ("قصى", "قصی"),  # Arabic alef maksura → Persian yeh
    ],
)
def test_arabic_to_persian_letters(raw: str, expected: str) -> None:
    assert normalize_persian_text(raw) == expected


def test_preserves_valid_halfspace() -> None:
    text = "می‌خواهم"
    result = normalize_persian_text(text)
    assert ZWNJ in result
    assert result == "می‌خواهم"


def test_never_removes_morphological_zwnj_variants() -> None:
    cases = [
        "کتاب‌ها",
        "نمی‌دانم",
        "استفاده‌نشده",
        "نوین‌پرداز",
    ]
    for text in cases:
        assert normalize_persian_text(text) == text


def test_collapses_duplicate_zwnj_but_keeps_one() -> None:
    raw = f"می{ZWNJ}{ZWNJ}خواهم"
    assert normalize_persian_text(raw) == "می‌خواهم"


def test_removes_orphaned_edge_zwnj() -> None:
    raw = f" {ZWNJ}مرخصی{ZWNJ} "
    assert normalize_persian_text(raw) == "مرخصی"


def test_removes_zwnj_adjacent_to_whitespace() -> None:
    raw = f"می {ZWNJ} خواهم"
    assert normalize_persian_text(raw) == "می خواهم"


def test_preserves_paragraph_breaks() -> None:
    text = "بند اول\n\nبند دوم"
    assert normalize_persian_text(text) == "بند اول\n\nبند دوم"


def test_collapses_inline_whitespace() -> None:
    assert normalize_persian_text("سلام    دنیا") == "سلام دنیا"


def test_normalizes_crlf_line_endings() -> None:
    assert normalize_persian_text("الف\r\nب\rپ") == "الف\nب\nپ"


def test_removes_tatweel() -> None:
    assert normalize_persian_text("کشـاورزی") == "کشاورزی"


def test_removes_arabic_diacritics() -> None:
    raw = "کِتابًا"
    assert normalize_persian_text(raw) == "کتابا"


def test_preserves_persian_ezafe_hamza() -> None:
    assert normalize_persian_text("مقایسهٔ بیان‌شده") == "مقایسهٔ بیان‌شده"


def test_unicode_nfc() -> None:
    # Alef + hamza above as combining sequence vs precomposed.
    decomposed = "ا\u0654"
    composed = unicodedata.normalize("NFC", decomposed)
    assert normalize_persian_text(decomposed) == normalize_persian_text(composed)


def test_persian_and_arabic_indic_digits_to_latin() -> None:
    assert normalize_persian_text("۲۰ روز و ١٢٣ و 45") == "20 روز و 123 و 45"


def test_persian_punctuation_kept_and_fullwidth_mapped() -> None:
    raw = "آیا درست است？ بله， درست؛"
    assert normalize_persian_text(raw) == "آیا درست است؟ بله، درست؛"


def test_collapses_repeated_punctuation_keeps_ellipsis() -> None:
    assert normalize_persian_text("واقعا!!! درست؟؟؟") == "واقعا! درست؟"
    assert normalize_persian_text("صبر.... بعد") == "صبر... بعد"
    assert normalize_persian_text("لیست،، مورد") == "لیست، مورد"


def test_persian_guillemets_preserved() -> None:
    assert normalize_persian_text("«نقل قول»") == "«نقل قول»"


def test_latin_curly_quotes_normalized() -> None:
    raw = "“quote” و ‘tick’"
    assert normalize_persian_text(raw) == "\"quote\" و 'tick'"


def test_invisible_unicode_cleanup() -> None:
    raw = "الف\u200b\ufeffب\u00adپ"
    assert normalize_persian_text(raw) == "الفبپ"


def test_office_and_pdf_spacing_artifacts() -> None:
    raw = "متن\u00a0با\u2003فاصله\u2009خاص"
    assert normalize_persian_text(raw) == "متن با فاصله خاص"


def test_strips_control_chars_keeps_newline_collapses_tab() -> None:
    raw = "سلام\x00دنیا\tخوب\x07است\nخط"
    # Tabs collapse with whitespace; newlines are preserved.
    assert normalize_persian_text(raw) == "سلامدنیا خوباست\nخط"


def test_ocr_like_noise_letters_digits_tatweel() -> None:
    raw = "كشـاورزي\u064b  ۱۲"
    assert normalize_persian_text(raw) == "کشاورزی 12"


def test_idempotent_on_diverse_inputs() -> None:
    samples = [
        "علي كتاب",
        "می‌خواهم",
        "سلام    دنیا",
        "۱۲۳ و 456 و ١٢٣",
        "کشـاورزیً",
        '«نقل» و "quote" و “curly”',
        "a\u200b\ufeffb\u00adm",
        f"می{ZWNJ}{ZWNJ}خواهم",
        f" مرخصی{ZWNJ} ",
        "آیا درست است？",
        "خط۱\r\nخط۲",
        "متن\u00a0فاصله",
    ]
    for sample in samples:
        once = normalize_persian_text(sample)
        twice = normalize_persian_text(once)
        assert once == twice, sample


def test_deterministic_repeated_calls() -> None:
    raw = "علي\u200b كتابـ ۱۲۳"
    assert normalize_persian_text(raw) == normalize_persian_text(raw)
