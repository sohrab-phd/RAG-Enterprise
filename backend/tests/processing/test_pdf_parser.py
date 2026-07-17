"""PDF parser reconstruction tests."""

from __future__ import annotations

from pathlib import Path

import fitz

from rag_enterprise.processing.parsers.pdf import (
    _clean_pdf_text,
    extract_text_from_rawdict,
    parse_pdf,
    remove_repeated_marginal_lines,
)


def _char(x0: float, x1: float, c: str, *, y0: float = 100.0, y1: float = 112.0) -> dict:
    return {"c": c, "bbox": [x0, y0, x1, y1]}


def _visual_row(
    visual_text: str,
    *,
    x_right: float = 200.0,
    y0: float = 100.0,
) -> dict:
    """Build chars in visual right-to-left order for rawdict tests."""
    chars: list[dict] = []
    x = x_right
    for value in visual_text:
        chars.append(_char(x - 6, x, value, y0=y0, y1=y0 + 12))
        x -= 6
    return {"spans": [{"text": visual_text, "chars": chars}]}


def test_rtl_gap_join_rebuilds_fragmented_persian_word() -> None:
    # Visual RTL fragments: "... فرآ" then "یند ..." as adjacent glyph runs.
    # Reading order after rebuild should contain "فرآیند".
    raw = {
        "blocks": [
            {
                "type": 0,
                "lines": [
                    {
                        "spans": [
                            {
                                "text": "فرآ",
                                "chars": [
                                    _char(70, 75, "ف"),
                                    _char(64, 70, "ر"),
                                    _char(58, 64, "آ"),
                                ],
                            }
                        ]
                    },
                    {
                        "spans": [
                            {
                                "text": "یند",
                                "chars": [
                                    _char(52, 58, "ی"),
                                    _char(46, 52, "ن"),
                                    _char(40, 46, "د"),
                                ],
                            }
                        ]
                    },
                ],
            }
        ]
    }

    text = extract_text_from_rawdict(raw)
    assert "فرآیند" in text


def test_rtl_gap_join_keeps_space_between_words() -> None:
    # Two words with a clear horizontal gap: "بین" then "دو".
    raw = {
        "blocks": [
            {
                "type": 0,
                "lines": [
                    {
                        "spans": [
                            {
                                "text": "بین",
                                "chars": [
                                    _char(90, 96, "ب"),
                                    _char(84, 90, "ی"),
                                    _char(78, 84, "ن"),
                                ],
                            }
                        ]
                    },
                    {
                        "spans": [
                            {
                                "text": "دو",
                                "chars": [
                                    _char(60, 66, "د"),
                                    _char(54, 60, "و"),
                                ],
                            }
                        ]
                    },
                ],
            }
        ]
    }

    text = extract_text_from_rawdict(raw)
    assert "بین دو" in text


def test_rtl_geometry_preserves_logical_digit_order_without_guessing() -> None:
    # PyMuPDF's span order is logical even when digit X coordinates are LTR.
    chars = [
        _char(194, 200, "س"),
        _char(188, 194, "ق"),
        _char(182, 188, "ف"),
        _char(164, 170, "2"),
        _char(170, 176, "0"),
        _char(158, 164, "ا"),
        _char(152, 158, "س"),
        _char(146, 152, "ت"),
    ]
    raw = {
        "width": 300,
        "blocks": [
            {
                "type": 0,
                "bbox": [20, 90, 220, 120],
                "lines": [
                    {
                        "spans": [
                            {
                                "text": "سقف20است",
                                "chars": chars,
                            }
                        ]
                    }
                ],
            }
        ],
    }

    text = extract_text_from_rawdict(raw)
    assert text == "سقف20است"
    assert "02" not in text


def test_rtl_geometry_preserves_mixed_latin_phrase() -> None:
    # Span order remains authoritative for embedded Latin text.
    raw = {
        "width": 400,
        "blocks": [
            {
                "type": 0,
                "bbox": [20, 90, 350, 120],
                "lines": [_visual_row("مرورگرGoogle Chromeاست")],
            }
        ],
    }

    text = extract_text_from_rawdict(raw)
    assert "Google Chrome" in text


def test_faq_question_answer_boundary_is_preserved() -> None:
    raw = {
        "width": 400,
        "blocks": [
            {
                "type": 0,
                "bbox": [20, 50, 380, 120],
                "lines": [
                    _visual_row("رمز اولیه چیست؟", y0=50),
                    _visual_row("کد ملی دانشجو است.", y0=70),
                    _visual_row("این پاسخ ادامه دارد.", y0=90),
                ],
            }
        ],
    }

    text = extract_text_from_rawdict(raw)
    lines = text.splitlines()
    assert lines[0] == "رمز اولیه چیست؟"
    assert lines[1].startswith("کد ملی")
    assert "این پاسخ ادامه دارد." in text


def test_wrapped_answer_blocks_join_but_question_boundary_remains() -> None:
    raw = {
        "width": 400,
        "blocks": [
            {
                "type": 0,
                "bbox": [150, 50, 380, 65],
                "lines": [_visual_row("رمز اولیه چیست؟", x_right=370, y0=50)],
            },
            {
                "type": 0,
                "bbox": [80, 85, 380, 100],
                "lines": [_visual_row("رمز اولیه کد ملی", x_right=370, y0=85)],
            },
            {
                "type": 0,
                "bbox": [300, 105, 380, 120],
                "lines": [_visual_row("دانشجو است.", x_right=370, y0=105)],
            },
        ],
    }

    text = extract_text_from_rawdict(raw)
    assert text == "رمز اولیه چیست؟\n\nرمز اولیه کد ملی دانشجو است."


def test_known_glyph_order_artifact_is_repaired_exactly() -> None:
    raw = {
        "width": 400,
        "blocks": [
            {
                "type": 0,
                "bbox": [80, 50, 380, 70],
                "lines": [_visual_row("اطالعات ورود", x_right=370, y0=50)],
            }
        ],
    }

    text = extract_text_from_rawdict(raw)
    assert _clean_pdf_text(text) == "اطلاعات ورود"


def test_two_column_persian_page_reads_right_column_first() -> None:
    raw = {
        "width": 600,
        "blocks": [
            {
                "type": 0,
                "bbox": [340, 60, 560, 90],
                "lines": [_visual_row("راست بالا", x_right=550, y0=60)],
            },
            {
                "type": 0,
                "bbox": [340, 120, 560, 150],
                "lines": [_visual_row("راست پایین", x_right=550, y0=120)],
            },
            {
                "type": 0,
                "bbox": [40, 60, 260, 90],
                "lines": [_visual_row("چپ بالا", x_right=250, y0=60)],
            },
            {
                "type": 0,
                "bbox": [40, 120, 260, 150],
                "lines": [_visual_row("چپ پایین", x_right=250, y0=120)],
            },
        ],
    }

    text = extract_text_from_rawdict(raw)
    assert text.index("راست بالا") < text.index("راست پایین")
    assert text.index("راست پایین") < text.index("چپ بالا")
    assert text.index("چپ بالا") < text.index("چپ پایین")


def test_repeated_headers_and_footers_are_removed_only_at_margins() -> None:
    pages = [
        "راهنمای سامانه گلستان\nمتن صفحه اول\nدانشگاه نمونه - صفحه 1",
        "راهنمای سامانه گلستان\nمتن صفحه دوم\nدانشگاه نمونه - صفحه 2",
        "راهنمای سامانه گلستان\nمتن صفحه سوم\nدانشگاه نمونه - صفحه 3",
    ]

    cleaned, removed = remove_repeated_marginal_lines(pages)

    assert removed == 6
    assert all("راهنمای سامانه گلستان" not in page for page in cleaned)
    assert all("دانشگاه نمونه" not in page for page in cleaned)
    assert cleaned == ["متن صفحه اول", "متن صفحه دوم", "متن صفحه سوم"]


def test_rtl_question_mark_stays_at_logical_line_end() -> None:
    raw = {
        "width": 300,
        "blocks": [
            {
                "type": 0,
                "bbox": [20, 90, 250, 120],
                "lines": [_visual_row("اطلاعات چیست؟")],
            }
        ],
    }

    assert extract_text_from_rawdict(raw).endswith("؟")


def test_parse_local_persian_pdf_has_clean_text_when_fixture_is_present() -> None:
    import pytest

    source = next(Path("storage/uploads").rglob("*.pdf"), None)
    if source is None:
        pytest.skip("Local Persian PDF fixture not present")

    result = parse_pdf(source)
    assert result.parser == "pdf"
    assert len(result.text) >= 100
    assert "\ufffd" not in result.text
    assert "arabic_script_pdf_reordered" in result.warnings


def test_parse_pdf_english_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "en.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Hello PDF paragraph\n\nSecond line")
    document.save(path)
    document.close()

    result = parse_pdf(path)
    assert "Hello PDF paragraph" in result.text
    assert "arabic_script_pdf_reordered" not in result.warnings
