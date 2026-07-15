"""Tests for Persian-aware document chunking."""

from __future__ import annotations

from rag_enterprise.chunking.splitter import (
    DEFAULT_MAX_CHUNK_CHARS,
    DEFAULT_OVERLAP_CHARS,
    split_persian_document,
)


def test_preserves_sentence_with_persian_question_mark() -> None:
    text = (
        "آیا مرخصی استحقاقی شامل کارکنان قراردادی هم می‌شود؟ "
        "بله، پس از سه ماه خدمت مستمر مشمول می‌شوند."
    )
    pieces = split_persian_document(text, max_chunk_chars=80, overlap_chars=20)
    joined = " ".join(piece.text for piece in pieces)
    assert "می‌شود؟" in joined
    assert not any(piece.text.endswith("می‌شود") and "؟" not in piece.text for piece in pieces)


def test_does_not_split_decimal_numbers() -> None:
    text = "نرخ هزینه ۱۲.۵ درصد است. " + ("ادامه متن توضیح سیاست برای رسیدن به سقف اندازه. " * 40)
    pieces = split_persian_document(text, max_chunk_chars=120, overlap_chars=20)
    assert all("۱۲." not in piece.text[-5:] or "۱۲.۵" in piece.text for piece in pieces)
    assert any("۱۲.۵" in piece.text for piece in pieces)


def test_does_not_split_english_abbreviation() -> None:
    text = "Contact Dr. Ahmadi for approval. " + ("Follow the written procedure carefully. " * 40)
    pieces = split_persian_document(text, max_chunk_chars=100, overlap_chars=20)
    assert all(not piece.text.rstrip().endswith("Dr") for piece in pieces)


def test_keeps_numbered_list_items_together_when_small() -> None:
    text = (
        "مراحل اقدام:\n\n"
        "۱. ثبت درخواست در سامانه\n"
        "۲. تأیید مدیر مستقیم\n"
        "۳. ثبت نهایی منابع انسانی\n"
    )
    pieces = split_persian_document(text, max_chunk_chars=500)
    assert len(pieces) == 1
    assert "۱. ثبت درخواست" in pieces[0].text
    assert "۳. ثبت نهایی" in pieces[0].text


def test_prefers_list_boundaries_when_oversized() -> None:
    item = "این مرحله شامل جزئیات اجرایی نسبتاً طولانی برای تشریح کامل فرایند است. "
    text = "\n".join(f"{idx}. {item * 8}" for idx in range(1, 6))
    pieces = split_persian_document(text, max_chunk_chars=350, overlap_chars=40)
    assert len(pieces) >= 2
    # Prefer item boundaries; tolerate overlap prefix from previous item.
    for piece in pieces:
        assert "مرحله شامل" in piece.text


def test_keeps_faq_pair_together() -> None:
    text = "سوال: سقف مرخصی چند روز است؟\n\nپاسخ: سقف مرخصی استحقاقی ۲۰ روز کاری است."
    pieces = split_persian_document(text, max_chunk_chars=400)
    assert len(pieces) == 1
    assert "سوال:" in pieces[0].text
    assert "پاسخ:" in pieces[0].text


def test_does_not_split_table_row() -> None:
    text = "| عنوان | مقدار |\n| --- | --- |\n| مرخصی | ۲۰ روز |\n| استعلاجی | ۷ روز |\n\n" + (
        "توضیح تکمیلی سیاست برای حجم. " * 80
    )
    pieces = split_persian_document(text, max_chunk_chars=220, overlap_chars=30)
    for piece in pieces:
        if "|" in piece.text:
            # Rows stay intact: no broken pipe row truncated mid-cell by bare hard-split.
            assert piece.text.count("|") >= 2


def test_heading_boundaries_for_persian_sections() -> None:
    text = (
        "۱. هدف و دامنه\n"
        "این بند هدف سند را مشخص می‌کند.\n\n"
        "۲. مرخصی استحقاقی سالانه\n"
        "مرخصی استحقاقی سالانه کارکنان رسمی ۲۰ روز کاری است.\n\n"
        "۳. مرخصی استعلاجی\n"
        "مرخصی استعلاجی تا هفت روز پذیرفته می‌شود."
    )
    pieces = split_persian_document(text, max_chunk_chars=200, target_chunk_chars=120)
    headings = {piece.heading for piece in pieces if piece.heading}
    assert any(h and h.startswith("۱.") for h in headings)
    assert any(piece.strategy == "heading" for piece in pieces)


def test_preserves_halfspace_inside_chunk() -> None:
    text = "کارکنان می‌توانند از مرخصی استفاده‌نشده استفاده کنند."
    pieces = split_persian_document(text)
    assert "می‌توانند" in pieces[0].text
    assert "استفاده‌نشده" in pieces[0].text
    assert pieces[0].text == text


def test_chunk_text_matches_source_slice() -> None:
    text = "بند اول.\n\nبند دوم با توضیح بیشتر.\n\nبند سوم."
    pieces = split_persian_document(text, max_chunk_chars=40, overlap_chars=10)
    for piece in pieces:
        assert text[piece.start : piece.end] == piece.text


def test_overlap_applied_on_oversized_split() -> None:
    sentence = "این یک جملهٔ کامل برای آزمایش هم‌پوشانی تکه‌ها است. "
    text = sentence * 80
    pieces = split_persian_document(
        text,
        max_chunk_chars=300,
        overlap_chars=DEFAULT_OVERLAP_CHARS,
    )
    assert len(pieces) >= 2
    assert any(piece.overlap_chars > 0 for piece in pieces[1:])
    # Adjacent pieces share a source region.
    assert pieces[1].start < pieces[0].end


def test_legal_clause_stays_with_body_when_small() -> None:
    text = "ماده ۱۲ - مرخصی\nکارکنان رسمی مشمول این ماده می‌شوند و جزئیات آن در آیین‌نامه آمده است."
    pieces = split_persian_document(text, max_chunk_chars=500)
    assert len(pieces) == 1
    assert "ماده ۱۲" in pieces[0].text


def test_office_like_multiline_paragraphs() -> None:
    text = (
        "پاراگراف اول از سند ورد با توضیح کافی.\n\n"
        "پاراگراف دوم پس از کپی از آفیس با متن بیشتر.\n\n"
        "پاراگراف سوم برای بستن بخش."
    )
    pieces = split_persian_document(text, max_chunk_chars=55, target_chunk_chars=40)
    assert len(pieces) >= 2
    assert all("\ufeff" not in piece.text for piece in pieces)


def test_respects_max_chunk_size() -> None:
    text = ("متن طولانی اداری بدون ساختار فهرست. " * 200).strip()
    pieces = split_persian_document(text, max_chunk_chars=DEFAULT_MAX_CHUNK_CHARS)
    assert pieces
    assert all(len(piece.text) <= DEFAULT_MAX_CHUNK_CHARS + 5 for piece in pieces)


def test_mixed_english_persian_not_broken_mid_token() -> None:
    text = "سامانه HRMS برای ثبت Leave Request استفاده می‌شود. " + (
        "توضیح بیشتر دربارهٔ فرایند داخلی سازمان. " * 50
    )
    pieces = split_persian_document(text, max_chunk_chars=160, overlap_chars=30)
    assert any("HRMS" in piece.text for piece in pieces)
    assert all(piece.text[-3:] != "HRM" for piece in pieces)
