"""PDF parser reconstruction tests."""

from __future__ import annotations

from pathlib import Path

import fitz

from rag_enterprise.processing.parsers.pdf import (
    extract_text_from_rawdict,
    parse_pdf,
)


def _char(x0: float, x1: float, c: str, *, y0: float = 100.0, y1: float = 112.0) -> dict:
    return {"c": c, "bbox": [x0, y0, x1, y1]}


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


def test_parse_pdf_persian_lotus_document_is_readable() -> None:
    import pytest

    source = next(Path("storage/uploads").rglob("*.pdf"), None)
    if source is None:
        pytest.skip("Local Persian PDF fixture not present")

    result = parse_pdf(source)
    assert result.parser == "pdf"
    assert "فرآیند" in result.text
    assert "یادگیری" in result.text
    assert "خط لوله" in result.text
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
