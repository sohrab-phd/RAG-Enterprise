"""PDF parser."""

from __future__ import annotations

import re
import statistics
import unicodedata
from pathlib import Path
from typing import Any

import fitz

from rag_enterprise.processing.exceptions import CorruptFileError, EncryptedPdfError
from rag_enterprise.processing.models import ParserOutput

_ARABIC_SCRIPT = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
_ROW_Y_TOLERANCE_FACTOR = 0.5
_SPACE_GAP_FACTOR = 0.4


def parse_pdf(path: Path) -> ParserOutput:
    """Extract text from PDF text layers using PyMuPDF."""
    try:
        document = fitz.open(path)
    except Exception as exc:
        raise CorruptFileError(f"Cannot parse PDF file: {path}") from exc

    try:
        if document.is_encrypted and not document.authenticate(""):
            raise EncryptedPdfError(f"PDF is encrypted: {path}")

        warnings: list[str] = []
        parts: list[str] = []
        arabic_reordered = False
        for index, page in enumerate(document, start=1):
            page_text, used_arabic_reorder = extract_page_text(page)
            arabic_reordered = arabic_reordered or used_arabic_reorder
            if not page_text:
                warnings.append(f"empty_page_{index}")
            else:
                parts.append(page_text)

        if arabic_reordered:
            warnings.append("arabic_script_pdf_reordered")

        return ParserOutput(
            text="\n\n".join(parts),
            parser="pdf",
            page_count=document.page_count,
            warnings=warnings,
        )
    finally:
        document.close()


def extract_page_text(page: fitz.Page) -> tuple[str, bool]:
    """Extract page text, reordering Arabic-script glyph runs when needed."""
    raw = page.get_text("rawdict")
    if not isinstance(raw, dict):
        return page.get_text().strip(), False

    if not _rawdict_has_arabic(raw):
        return page.get_text().strip(), False

    text = extract_text_from_rawdict(raw)
    # Compatibility forms from some Persian fonts (e.g. isolated glyphs).
    text = unicodedata.normalize("NFKC", text).strip()
    return text, True


def extract_text_from_rawdict(raw: dict[str, Any]) -> str:
    """Reconstruct reading-order text from a PyMuPDF rawdict structure."""
    parts: list[str] = []
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        block_text = _extract_block_text(block)
        if block_text.strip():
            parts.append(block_text)
    return "\n\n".join(parts)


def _rawdict_has_arabic(raw: dict[str, Any]) -> bool:
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                for char in span.get("chars", []):
                    value = char.get("c", "")
                    if value and _ARABIC_SCRIPT.search(value):
                        return True
                if _ARABIC_SCRIPT.search(span.get("text", "")):
                    return True
    return False


def _extract_block_text(block: dict[str, Any]) -> str:
    chars: list[tuple[float, float, float, float, str]] = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            for char in span.get("chars", []):
                value = char.get("c", "")
                if not value or value.isspace():
                    continue
                bbox = char.get("bbox")
                if not bbox or len(bbox) != 4:
                    continue
                x0, y0, x1, y1 = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
                chars.append((y0, y1, x0, x1, value))

    if not chars:
        return ""

    heights = [y1 - y0 for _, y1, _, _, _ in chars]
    median_height = statistics.median(heights) if heights else 10.0
    sample = "".join(value for *_, value in chars)
    arabic = _is_mostly_arabic(sample)

    rows = _cluster_rows(chars, median_height)
    row_texts: list[str] = []
    for row_chars in rows:
        row_texts.append(_join_row_chars(row_chars, arabic=arabic))
    return "\n".join(row_texts)


def _is_mostly_arabic(sample: str) -> bool:
    letters = [char for char in sample if not char.isspace()]
    if not letters:
        return False
    arabic_count = sum(1 for char in letters if _ARABIC_SCRIPT.search(char))
    return arabic_count >= len(letters) / 2


def _cluster_rows(
    chars: list[tuple[float, float, float, float, str]],
    median_height: float,
) -> list[list[tuple[float, float, str]]]:
    tolerance = median_height * _ROW_Y_TOLERANCE_FACTOR
    rows: list[tuple[float, list[tuple[float, float, str]]]] = []
    for y0, _y1, x0, x1, value in sorted(chars, key=lambda item: item[0]):
        if not rows or abs(y0 - rows[-1][0]) > tolerance:
            rows.append((y0, [(x0, x1, value)]))
        else:
            rows[-1][1].append((x0, x1, value))
    return [row_chars for _, row_chars in rows]


def _join_row_chars(row_chars: list[tuple[float, float, str]], *, arabic: bool) -> str:
    widths = [max(0.1, x1 - x0) for x0, x1, _ in row_chars if (x1 - x0) > 0.5]
    median_width = statistics.median(widths) if widths else 5.0
    space_gap = median_width * _SPACE_GAP_FACTOR
    ordered = sorted(row_chars, key=lambda item: -item[0] if arabic else item[0])

    parts: list[str] = []
    previous: tuple[float, float] | None = None
    for x0, x1, value in ordered:
        if previous is not None:
            gap = (previous[0] - x1) if arabic else (x0 - previous[1])
            if gap > space_gap:
                parts.append(" ")
        parts.append(value)
        previous = (x0, x1)
    return "".join(parts)
