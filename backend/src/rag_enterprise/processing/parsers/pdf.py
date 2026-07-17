"""Persian-aware PDF text-layer extraction.

The parser deliberately performs only deterministic, geometry-backed repairs.
It never applies dictionary substitutions or guesses corrupted numbers.
"""

from __future__ import annotations

import math
import re
import statistics
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz

from rag_enterprise.processing.exceptions import CorruptFileError, EncryptedPdfError
from rag_enterprise.processing.models import ParserOutput

_ARABIC_SCRIPT = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
_ARABIC_LETTER = re.compile(r"[\u0621-\u063A\u0641-\u064A\u066E-\u06D3\u06FA-\u06FF]")
_BULLET_PREFIX = re.compile(r"^(?:[-•▪●○*]|\d{1,3}[.)])\s*")
_SENTENCE_END = frozenset(".!؟?؛;:")
_ROW_Y_TOLERANCE_FACTOR = 0.5
_SPACE_GAP_FACTOR = 0.4
_COLUMN_MAX_WIDTH_RATIO = 0.62
_COLUMN_SIDE_BOUNDARY = 0.58
_MARGINAL_LINE_LIMIT = 2
_MIN_REPEATED_MARGIN_RATIO = 0.6
_SAFE_PDF_ARTIFACTS = {
    "اطالعات": "اطلاعات",
}


@dataclass(frozen=True)
class PdfTextDiagnostics:
    """Deterministic extraction-quality counters exposed through warnings."""

    arabic_pages: int = 0
    geometry_pages: int = 0
    fallback_pages: int = 0
    repeated_margin_lines_removed: int = 0
    replacement_characters: int = 0
    presentation_form_characters: int = 0
    deterministic_repairs: int = 0

    def warnings(self) -> list[str]:
        """Return stable metadata warnings for persisted extraction diagnostics."""
        values = [
            f"pdf_arabic_pages:{self.arabic_pages}",
            f"pdf_geometry_pages:{self.geometry_pages}",
            f"pdf_fallback_pages:{self.fallback_pages}",
            f"pdf_repeated_margin_lines_removed:{self.repeated_margin_lines_removed}",
            f"pdf_replacement_characters:{self.replacement_characters}",
            f"pdf_presentation_form_characters:{self.presentation_form_characters}",
            f"pdf_deterministic_repairs:{self.deterministic_repairs}",
        ]
        return values


def parse_pdf(path: Path) -> ParserOutput:
    """Extract text using sorted text or Persian geometry reconstruction."""
    try:
        document = fitz.open(path)
    except Exception as exc:
        raise CorruptFileError(f"Cannot parse PDF file: {path}") from exc

    try:
        if document.is_encrypted and not document.authenticate(""):
            raise EncryptedPdfError(f"PDF is encrypted: {path}")

        warnings: list[str] = []
        pages: list[str] = []
        arabic_pages = 0
        geometry_pages = 0
        fallback_pages = 0
        presentation_forms = 0
        deterministic_repairs = 0
        for index, page in enumerate(document, start=1):
            raw = page.get_text("rawdict")
            presentation_forms += _count_presentation_forms(raw)
            deterministic_repairs += _count_safe_artifacts(raw)
            page_text, used_arabic_reorder = extract_page_text(page, raw=raw)
            if used_arabic_reorder:
                arabic_pages += 1
                geometry_pages += 1
            else:
                fallback_pages += 1
            if not page_text:
                warnings.append(f"empty_page_{index}")
            pages.append(page_text)

        cleaned_pages, removed_margin_lines = remove_repeated_marginal_lines(pages)
        text = "\n\n".join(page for page in cleaned_pages if page.strip())
        diagnostics = PdfTextDiagnostics(
            arabic_pages=arabic_pages,
            geometry_pages=geometry_pages,
            fallback_pages=fallback_pages,
            repeated_margin_lines_removed=removed_margin_lines,
            replacement_characters=text.count("\ufffd"),
            presentation_form_characters=presentation_forms,
            deterministic_repairs=deterministic_repairs,
        )

        if geometry_pages:
            warnings.append("arabic_script_pdf_reordered")
        if removed_margin_lines:
            warnings.append("repeated_pdf_margins_removed")
        warnings.extend(diagnostics.warnings())

        return ParserOutput(
            text=text,
            parser="pdf",
            page_count=document.page_count,
            warnings=warnings,
        )
    finally:
        document.close()


def extract_page_text(
    page: fitz.Page,
    *,
    raw: dict[str, Any] | None = None,
) -> tuple[str, bool]:
    """Choose the safest extraction strategy for one page.

    English / non-Arabic pages use PyMuPDF's sorted text mode. Arabic-script
    pages use glyph geometry with bidirectional run repair.
    """
    if raw is None:
        raw = page.get_text("rawdict")
    if not isinstance(raw, dict):
        return page.get_text("text", sort=True).strip(), False

    if not _rawdict_has_arabic(raw):
        return page.get_text("text", sort=True).strip(), False

    text = extract_text_from_rawdict(raw)
    # Compatibility forms from some Persian fonts (e.g. isolated glyphs).
    text = _clean_pdf_text(unicodedata.normalize("NFKC", text)).strip()
    return text, True


def extract_text_from_rawdict(raw: dict[str, Any]) -> str:
    """Reconstruct Persian reading order from a PyMuPDF raw dictionary."""
    blocks: list[_TextBlock] = []
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        block_text = _extract_block_text(block)
        if block_text.strip():
            blocks.append(
                _TextBlock(
                    bbox=_block_bbox(block),
                    text=_reflow_block(block_text),
                    is_arabic=_is_mostly_arabic(block_text),
                )
            )
    ordered = _order_text_blocks(
        blocks,
        page_width=float(raw.get("width") or 0.0),
    )
    return _join_wrapped_blocks(ordered)


@dataclass(frozen=True)
class _TextBlock:
    bbox: tuple[float, float, float, float]
    text: str
    is_arabic: bool


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
    runs: list[_TextRun] = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            run = _text_run_from_span(span)
            if run is not None:
                runs.append(run)

    if not runs:
        return ""

    heights = [run.y1 - run.y0 for run in runs]
    median_height = statistics.median(heights) if heights else 10.0
    sample = "".join(run.text for run in runs)
    arabic = _is_mostly_arabic(sample)

    rows = _cluster_text_runs(runs, median_height)
    row_texts: list[str] = []
    for row_runs in rows:
        row_texts.append(_join_row_runs(row_runs, arabic=arabic))
    return "\n".join(row_texts)


@dataclass(frozen=True)
class _TextRun:
    y0: float
    y1: float
    x0: float
    x1: float
    text: str


def _text_run_from_span(span: dict[str, Any]) -> _TextRun | None:
    """Preserve PyMuPDF's logical character order inside one font span."""
    values: list[str] = []
    boxes: list[tuple[float, float, float, float]] = []
    for char in span.get("chars", []):
        value = char.get("c", "")
        bbox = char.get("bbox")
        if not value or not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            continue
        values.append(value)
        boxes.append(
            (
                float(bbox[0]),
                float(bbox[1]),
                float(bbox[2]),
                float(bbox[3]),
            )
        )
    if not values or not boxes:
        return None
    return _TextRun(
        y0=min(box[1] for box in boxes),
        y1=max(box[3] for box in boxes),
        x0=min(box[0] for box in boxes),
        x1=max(box[2] for box in boxes),
        text="".join(values).replace("\u00a0", " "),
    )


def _cluster_text_runs(
    runs: list[_TextRun],
    median_height: float,
) -> list[list[_TextRun]]:
    tolerance = median_height * _ROW_Y_TOLERANCE_FACTOR
    rows: list[tuple[float, list[_TextRun]]] = []
    for run in sorted(runs, key=lambda item: item.y0):
        if not rows or abs(run.y0 - rows[-1][0]) > tolerance:
            rows.append((run.y0, [run]))
        else:
            rows[-1][1].append(run)
    return [row_runs for _, row_runs in rows]


def _join_row_runs(row_runs: list[_TextRun], *, arabic: bool) -> str:
    widths = [
        (run.x1 - run.x0) / max(1, len(run.text.strip()))
        for run in row_runs
        if run.text.strip() and run.x1 > run.x0
    ]
    median_width = statistics.median(widths) if widths else 5.0
    space_gap = median_width * _SPACE_GAP_FACTOR
    ordered = sorted(row_runs, key=lambda run: -run.x0 if arabic else run.x0)

    parts: list[str] = []
    previous: _TextRun | None = None
    for run in ordered:
        if previous is not None:
            gap = (previous.x0 - run.x1) if arabic else (run.x0 - previous.x1)
            previous_has_space = bool(parts and parts[-1].endswith(" "))
            if gap > space_gap and not previous_has_space and not run.text.startswith(" "):
                parts.append(" ")
        parts.append(run.text)
        previous = run
    return "".join(parts).strip()


def _is_mostly_arabic(sample: str) -> bool:
    letters = [char for char in sample if unicodedata.category(char).startswith("L")]
    if not letters:
        return False
    arabic_count = sum(1 for char in letters if _ARABIC_SCRIPT.search(char))
    # A Persian sentence can contain a long URL or product name. Unicode BiDi
    # defaults such mixed lines to RTL well below a 50% Arabic-letter ratio.
    return arabic_count / len(letters) >= 0.3


def _block_bbox(block: dict[str, Any]) -> tuple[float, float, float, float]:
    bbox = block.get("bbox")
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        return (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))

    char_boxes: list[tuple[float, float, float, float]] = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            for char in span.get("chars", []):
                char_bbox = char.get("bbox")
                if isinstance(char_bbox, (list, tuple)) and len(char_bbox) == 4:
                    char_boxes.append(
                        (
                            float(char_bbox[0]),
                            float(char_bbox[1]),
                            float(char_bbox[2]),
                            float(char_bbox[3]),
                        )
                    )
    if not char_boxes:
        return (0.0, 0.0, 0.0, 0.0)
    return (
        min(box[0] for box in char_boxes),
        min(box[1] for box in char_boxes),
        max(box[2] for box in char_boxes),
        max(box[3] for box in char_boxes),
    )


def _order_text_blocks(
    blocks: list[_TextBlock],
    *,
    page_width: float,
) -> list[_TextBlock]:
    """Order blocks top-to-bottom, with conservative two-column handling."""
    if len(blocks) < 4 or page_width <= 0:
        return sorted(blocks, key=lambda block: (block.bbox[1], block.bbox[0]))

    narrow = [
        block
        for block in blocks
        if (block.bbox[2] - block.bbox[0]) <= page_width * _COLUMN_MAX_WIDTH_RATIO
    ]
    left = [block for block in narrow if block.bbox[2] <= page_width * _COLUMN_SIDE_BOUNDARY]
    right = [
        block for block in narrow if block.bbox[0] >= page_width * (1.0 - _COLUMN_SIDE_BOUNDARY)
    ]
    if len(left) < 2 or len(right) < 2 or not _vertical_ranges_overlap(left, right):
        return sorted(blocks, key=lambda block: (block.bbox[1], block.bbox[0]))

    column_ids = {id(block) for block in [*left, *right]}
    full_width = [block for block in blocks if id(block) not in column_ids]
    first_column_y = min(block.bbox[1] for block in [*left, *right])
    last_column_y = max(block.bbox[3] for block in [*left, *right])
    before = [block for block in full_width if block.bbox[3] <= first_column_y]
    after = [block for block in full_width if block.bbox[1] >= last_column_y]
    middle = [block for block in full_width if block not in before and block not in after]

    mostly_arabic = (
        sum(1 for block in [*left, *right] if block.is_arabic) >= (len(left) + len(right)) / 2
    )
    first, second = (right, left) if mostly_arabic else (left, right)

    def by_y(block: _TextBlock) -> tuple[float, float]:
        return (block.bbox[1], block.bbox[0])

    return [
        *sorted(before, key=by_y),
        *sorted(first, key=by_y),
        *sorted(second, key=by_y),
        *sorted(middle, key=by_y),
        *sorted(after, key=by_y),
    ]


def _join_wrapped_blocks(blocks: list[_TextBlock]) -> str:
    """Join adjacent visual lines while retaining semantic block boundaries."""
    if not blocks:
        return ""
    heights = [block.bbox[3] - block.bbox[1] for block in blocks if block.bbox[3] > block.bbox[1]]
    median_height = statistics.median(heights) if heights else 15.0
    paragraphs: list[str] = []
    current = blocks[0].text
    previous = blocks[0]
    for block in blocks[1:]:
        if _blocks_form_wrapped_line(previous, block, median_height):
            current = f"{current.rstrip()} {block.text.lstrip()}"
        else:
            paragraphs.append(current)
            current = block.text
        previous = block
    paragraphs.append(current)
    return "\n\n".join(paragraph.strip() for paragraph in paragraphs if paragraph.strip())


def _blocks_form_wrapped_line(
    previous: _TextBlock,
    current: _TextBlock,
    median_height: float,
) -> bool:
    if previous.is_arabic != current.is_arabic:
        return False
    if _must_keep_line_break(previous.text.rstrip(), current.text.lstrip()):
        return False
    vertical_gap = current.bbox[1] - previous.bbox[3]
    if vertical_gap < -median_height * 0.25 or vertical_gap > median_height * 0.55:
        return False
    overlap = max(
        0.0,
        min(previous.bbox[2], current.bbox[2]) - max(previous.bbox[0], current.bbox[0]),
    )
    shortest_width = min(
        previous.bbox[2] - previous.bbox[0],
        current.bbox[2] - current.bbox[0],
    )
    return shortest_width > 0 and overlap / shortest_width >= 0.5


def _vertical_ranges_overlap(left: list[_TextBlock], right: list[_TextBlock]) -> bool:
    left_start = min(block.bbox[1] for block in left)
    left_end = max(block.bbox[3] for block in left)
    right_start = min(block.bbox[1] for block in right)
    right_end = max(block.bbox[3] for block in right)
    overlap = max(0.0, min(left_end, right_end) - max(left_start, right_start))
    shortest = min(left_end - left_start, right_end - right_start)
    return shortest > 0 and overlap / shortest >= 0.5


def _reflow_block(text: str) -> str:
    """Join visual wraps while preserving FAQ, headings, lists, and punctuation."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return text.strip()

    paragraphs: list[str] = []
    current = lines[0]
    for line in lines[1:]:
        if _must_keep_line_break(current, line):
            paragraphs.append(current)
            current = line
        else:
            current = f"{current} {line}"
    paragraphs.append(current)
    return "\n".join(paragraphs)


def _must_keep_line_break(previous: str, current: str) -> bool:
    if previous.endswith(("؟", "?")):
        return True
    if previous[-1:] in _SENTENCE_END:
        return True
    if _BULLET_PREFIX.match(previous) or _BULLET_PREFIX.match(current):
        return True
    return current.endswith(("؟", "?"))


def _clean_pdf_text(text: str) -> str:
    """Apply conservative PDF-only Unicode and RTL punctuation repairs."""
    cleaned = text
    for corrupt, replacement in _SAFE_PDF_ARTIFACTS.items():
        cleaned = re.sub(
            rf"(?<!{_ARABIC_LETTER.pattern}){re.escape(corrupt)}"
            rf"(?!{_ARABIC_LETTER.pattern})",
            replacement,
            cleaned,
        )
    lines: list[str] = []
    for line in cleaned.splitlines():
        value = re.sub(r"^،(\S+)", r"\1،", line)
        value = re.sub(r"\s+([،؛؟!,:»)\]}])", r"\1", value)
        value = re.sub(r"([،؛؟!:])(?=[^\s\n])", r"\1 ", value)
        lines.append(value)
    return "\n".join(lines)


def remove_repeated_marginal_lines(pages: list[str]) -> tuple[list[str], int]:
    """Remove recurring headers / footers only from page margins."""
    if len(pages) < 2:
        return pages, 0

    page_lines = [[line for line in page.splitlines() if line.strip()] for page in pages]
    occurrences: dict[str, int] = {}
    for lines in page_lines:
        candidates = [*lines[:_MARGINAL_LINE_LIMIT], *lines[-_MARGINAL_LINE_LIMIT:]]
        for key in {_margin_key(line) for line in candidates if _valid_margin_line(line)}:
            occurrences[key] = occurrences.get(key, 0) + 1

    threshold = max(2, math.ceil(len(pages) * _MIN_REPEATED_MARGIN_RATIO))
    repeated = {key for key, count in occurrences.items() if count >= threshold}
    if not repeated:
        return pages, 0

    cleaned: list[str] = []
    removed = 0
    for lines in page_lines:
        output: list[str] = []
        last_index = len(lines) - 1
        for index, line in enumerate(lines):
            in_margin = index < _MARGINAL_LINE_LIMIT or index > last_index - _MARGINAL_LINE_LIMIT
            if in_margin and _margin_key(line) in repeated:
                removed += 1
                continue
            output.append(line)
        cleaned.append("\n".join(output))
    return cleaned, removed


def _valid_margin_line(line: str) -> bool:
    stripped = line.strip()
    return 2 <= len(stripped) <= 120


def _margin_key(line: str) -> str:
    normalized = unicodedata.normalize("NFKC", line).casefold()
    if re.search(r"(?:صفحه|page)\s*[:#-]?\s*\d+", normalized):
        normalized = re.sub(r"\d+", "#", normalized)
    elif re.fullmatch(r"[\s\d۰-۹٠-٩./|_-]+", normalized):
        normalized = "#"
    return re.sub(r"\s+", " ", normalized).strip()


def _count_presentation_forms(raw: object) -> int:
    if not isinstance(raw, dict):
        return 0
    count = 0
    for block in raw.get("blocks", []):
        if not isinstance(block, dict):
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                for char in span.get("chars", []):
                    value = char.get("c", "")
                    count += sum(
                        1
                        for item in value
                        if "\ufb50" <= item <= "\ufdff" or "\ufe70" <= item <= "\ufeff"
                    )
    return count


def _count_safe_artifacts(raw: object) -> int:
    if not isinstance(raw, dict):
        return 0
    source = "".join(
        char.get("c", "")
        for block in raw.get("blocks", [])
        if isinstance(block, dict)
        for line in block.get("lines", [])
        for span in line.get("spans", [])
        for char in span.get("chars", [])
    )
    return sum(source.count(artifact) for artifact in _SAFE_PDF_ARTIFACTS)
