"""Persian-aware, structure-preserving text splitting (Feature 003).

Pure functions only — no I/O. Chunks are contiguous slices of the source text
(CH-06). Overlap is expressed as overlapping ``[start, end)`` ranges when a unit
must be force-split (SPEC §4.2 / §5.1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_MAX_CHUNK_CHARS = 1200
DEFAULT_MIN_CHUNK_CHARS = 50
DEFAULT_OVERLAP_CHARS = 125
DEFAULT_TARGET_CHUNK_CHARS = 1000

_BLANK_LINE_RE = re.compile(r"\n\s*\n+")
_MARKDOWN_HEADING_RE = re.compile(r"^#{1,6}\s+\S")
_SECTION_LABEL_RE = re.compile(
    r"^(?:ماده|بند|تبصره|فصل|بخش|قسمت|موضوع|عنوان|"
    r"مادهٔ|فصلِ)\s*[:.\-]?\s*[\d۰-۹٠-٩A-Za-z]+",
    re.UNICODE,
)
_NUMBERED_HEADING_RE = re.compile(
    r"^[\d۰-۹٠-٩]{1,3}[.\-)]\s+\S",
    re.UNICODE,
)
_LIST_ITEM_RE = re.compile(
    r"^(?:"
    r"[-•▪●○\*]"
    r"|[\d۰-۹٠-٩]{1,3}[.\)]"
    r"|[a-zA-Z][.\)]"
    r"|[الفبپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی][.\)]"
    r")\s+\S",
    re.UNICODE,
)
_FAQ_QUESTION_RE = re.compile(
    r"(?:^(?:سوال|سؤال|پرسش|Q|q)\s*[:.\-]|"
    r"[؟\?]\s*$)",
    re.UNICODE,
)
_TABLE_ROW_RE = re.compile(r"(?:\t.+\t)|(?:\|.+\|)")
_SENTENCE_END_CHARS = frozenset(".!?؟۔")
_ABBREVIATIONS = frozenset(
    {
        "mr",
        "mrs",
        "ms",
        "dr",
        "prof",
        "jr",
        "sr",
        "vs",
        "etc",
        "e.g",
        "i.e",
        "no",
        "nos",
        "vol",
        "fig",
        "approx",
        "approx.",
        "ص",
        "ق",
        "م",
        "ه.ش",
        "ه.ق",
        "ق.م",
        "ص.پ",
    }
)


@dataclass(frozen=True)
class ChunkPiece:
    """One contiguous chunk of the source document."""

    start: int
    end: int
    text: str
    heading: str | None
    strategy: str
    overlap_chars: int = 0


@dataclass(frozen=True)
class _Unit:
    start: int
    end: int
    kind: str  # heading | list | faq | table | clause | prose
    heading: str | None = None


def split_persian_document(
    text: str,
    *,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    min_chunk_chars: int = DEFAULT_MIN_CHUNK_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
    target_chunk_chars: int = DEFAULT_TARGET_CHUNK_CHARS,
) -> list[ChunkPiece]:
    """Split normalized document text into coherent chunks."""
    if not text:
        return []
    if not text.strip():
        return []

    paragraphs = _paragraph_units(text)
    units = _coalesce_semantic_units(text, paragraphs)
    has_heading = any(unit.kind == "heading" for unit in units)
    strategy = "heading" if has_heading else "paragraph"

    spans = _merge_units(
        text,
        units,
        max_chunk_chars=max_chunk_chars,
        min_chunk_chars=min_chunk_chars,
        overlap_chars=overlap_chars,
        target_chunk_chars=target_chunk_chars,
    )
    pieces: list[ChunkPiece] = []
    for start, end, overlap in spans:
        trimmed_start, trimmed_end = _trim_span(text, start, end)
        if trimmed_start >= trimmed_end:
            continue
        heading = _heading_covering(units, trimmed_start, trimmed_end)
        pieces.append(
            ChunkPiece(
                start=trimmed_start,
                end=trimmed_end,
                text=text[trimmed_start:trimmed_end],
                heading=heading,
                strategy=strategy,
                overlap_chars=overlap,
            )
        )

    if not pieces:
        start, end = _trim_span(text, 0, len(text))
        if start < end:
            pieces.append(
                ChunkPiece(
                    start=start,
                    end=end,
                    text=text[start:end],
                    heading=None,
                    strategy="paragraph",
                    overlap_chars=0,
                )
            )
    return pieces


def _heading_covering(units: list[_Unit], start: int, end: int) -> str | None:
    active: str | None = None
    for unit in units:
        if unit.end <= start:
            if unit.kind == "heading":
                active = unit.heading
            continue
        if unit.start >= end:
            break
        if unit.kind == "heading" and unit.heading:
            return unit.heading
    return active


def _paragraph_units(text: str) -> list[_Unit]:
    spans: list[tuple[int, int]] = []
    cursor = 0
    for match in _BLANK_LINE_RE.finditer(text):
        if match.start() > cursor:
            spans.append((cursor, match.start()))
        cursor = match.end()
    if cursor < len(text):
        spans.append((cursor, len(text)))
    if not spans:
        spans = [(0, len(text))]

    units: list[_Unit] = []
    for start, end in spans:
        units.extend(_units_from_block(text, start, end))
    return units


def _units_from_block(text: str, start: int, end: int) -> list[_Unit]:
    """Split a blank-line block; peel leading section titles into headings."""
    trimmed_start, trimmed_end = _trim_span(text, start, end)
    if trimmed_start >= trimmed_end:
        return []
    block = text[trimmed_start:trimmed_end]
    line_spans = _line_spans(block)
    if not line_spans:
        return []

    lines = [block[s:e].strip() for s, e in line_spans]
    first_line = lines[0]

    # Numbered/bulleted sequences are lists — never peel the first item as a section title.
    if len(lines) >= 2 and all(_LIST_ITEM_RE.match(line) for line in lines):
        return [_Unit(start=trimmed_start, end=trimmed_end, kind="list", heading=None)]

    if len(line_spans) >= 2 and _is_section_heading_line(first_line):
        heading_end_local = line_spans[0][1]
        heading_abs_start, heading_abs_end = _trim_span(
            text, trimmed_start, trimmed_start + heading_end_local
        )
        body_abs_start, body_abs_end = _trim_span(
            text, trimmed_start + line_spans[1][0], trimmed_end
        )
        result: list[_Unit] = []
        if heading_abs_start < heading_abs_end:
            result.append(
                _Unit(
                    start=heading_abs_start,
                    end=heading_abs_end,
                    kind="heading",
                    heading=first_line.lstrip("#").strip()[:500],
                )
            )
        if body_abs_start < body_abs_end:
            kind, heading = _classify_paragraph(text[body_abs_start:body_abs_end])
            result.append(_Unit(start=body_abs_start, end=body_abs_end, kind=kind, heading=heading))
        return result

    kind, heading = _classify_paragraph(block)
    return [_Unit(start=trimmed_start, end=trimmed_end, kind=kind, heading=heading)]


def _line_spans(block: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = 0
    for match in re.finditer(r"\n", block):
        if match.start() > cursor:
            spans.append((cursor, match.start()))
        cursor = match.end()
    if cursor < len(block):
        spans.append((cursor, len(block)))
    return [(s, e) for s, e in spans if block[s:e].strip()]


def _classify_paragraph(paragraph: str) -> tuple[str, str | None]:
    lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
    if not lines:
        return "prose", None
    first = lines[0]
    body = "\n".join(lines)

    if _TABLE_ROW_RE.search(body) or body.count("|") >= 2 or body.count("\t") >= 2:
        return "table", None
    if all(_LIST_ITEM_RE.match(line) for line in lines):
        return "list", None
    if _FAQ_QUESTION_RE.search(first) and len(lines) == 1:
        return "faq", None
    if _is_section_heading_line(first) and len(lines) == 1:
        return "heading", first.lstrip("#").strip()[:500]
    if _SECTION_LABEL_RE.match(first) and len(lines) > 1:
        return "clause", first[:500]
    return "prose", None


def _is_section_heading_line(line: str) -> bool:
    """True for section titles, not ordinary list items."""
    stripped = line.strip()
    if not stripped or len(stripped) > 120:
        return False
    if stripped.endswith(tuple(_SENTENCE_END_CHARS)):
        return False
    if _MARKDOWN_HEADING_RE.match(stripped):
        return True
    if _SECTION_LABEL_RE.match(stripped):
        return True
    if _NUMBERED_HEADING_RE.match(stripped):
        # Section titles are short labels (e.g. "۱. هدف و دامنه").
        return len(stripped) <= 60 and stripped.count(" ") <= 8
    return False


def _is_heading_line(line: str) -> bool:
    return _is_section_heading_line(line)


def _coalesce_semantic_units(text: str, paragraphs: list[_Unit]) -> list[_Unit]:
    if not paragraphs:
        return []
    coalesced: list[_Unit] = []
    index = 0
    while index < len(paragraphs):
        current = paragraphs[index]
        if current.kind == "list":
            end = current.end
            heading = current.heading
            index += 1
            while index < len(paragraphs) and paragraphs[index].kind == "list":
                end = paragraphs[index].end
                index += 1
            coalesced.append(_Unit(start=current.start, end=end, kind="list", heading=heading))
            continue
        if current.kind == "faq" and index + 1 < len(paragraphs):
            nxt = paragraphs[index + 1]
            pair_len = nxt.end - current.start
            if nxt.kind in {"prose", "clause", "list", "table"} and pair_len <= (
                DEFAULT_MAX_CHUNK_CHARS + DEFAULT_TARGET_CHUNK_CHARS
            ):
                coalesced.append(
                    _Unit(start=current.start, end=nxt.end, kind="faq", heading=current.heading)
                )
                index += 2
                continue
        if current.kind == "table":
            end = current.end
            index += 1
            while index < len(paragraphs) and paragraphs[index].kind == "table":
                end = paragraphs[index].end
                index += 1
            coalesced.append(_Unit(start=current.start, end=end, kind="table", heading=None))
            continue
        coalesced.append(current)
        index += 1
    return coalesced


def _merge_units(
    text: str,
    units: list[_Unit],
    *,
    max_chunk_chars: int,
    min_chunk_chars: int,
    overlap_chars: int,
    target_chunk_chars: int,
) -> list[tuple[int, int, int]]:
    if not units:
        return []

    spans: list[tuple[int, int, int]] = []
    buffer_start = units[0].start
    buffer_end = units[0].end
    buffer_has_structure = units[0].kind in {"list", "table", "faq", "clause"}

    def flush_buffer() -> None:
        nonlocal buffer_start, buffer_end, buffer_has_structure
        if buffer_start >= buffer_end:
            return
        prefer_list = buffer_has_structure
        for start, end, overlap in _split_span(
            text,
            buffer_start,
            buffer_end,
            max_chunk_chars=max_chunk_chars,
            overlap_chars=overlap_chars,
            prefer_list_breaks=prefer_list,
        ):
            spans.append((start, end, overlap))
        buffer_start = buffer_end
        buffer_has_structure = False

    for unit in units[1:]:
        # Prefer contiguous source spans; skip orphaned whitespace gaps by extending.
        join_end = unit.end
        candidate_len = join_end - buffer_start
        at_capacity = candidate_len > max_chunk_chars
        soft_boundary = (
            (buffer_end - buffer_start) >= target_chunk_chars
            and unit.kind in {"heading", "list", "table", "faq", "clause"}
            and (unit.end - unit.start) >= min_chunk_chars
        )
        if at_capacity or soft_boundary:
            flush_buffer()
            buffer_start = unit.start
            buffer_end = unit.end
            buffer_has_structure = unit.kind in {"list", "table", "faq", "clause"}
            if unit.end - unit.start > max_chunk_chars:
                flush_buffer()
        else:
            buffer_end = join_end
            buffer_has_structure = buffer_has_structure or unit.kind in {
                "list",
                "table",
                "faq",
                "clause",
            }

    flush_buffer()

    if len(spans) >= 2:
        last_start, last_end, _last_overlap = spans[-1]
        if (last_end - last_start) < min_chunk_chars:
            prev_start, _prev_end, prev_overlap = spans[-2]
            if (last_end - prev_start) <= max_chunk_chars:
                spans[-2] = (prev_start, last_end, prev_overlap)
                spans.pop()

    return spans


def _split_span(
    text: str,
    start: int,
    end: int,
    *,
    max_chunk_chars: int,
    overlap_chars: int,
    prefer_list_breaks: bool,
) -> list[tuple[int, int, int]]:
    length = end - start
    if length <= max_chunk_chars:
        return [(start, end, 0)]

    region = text[start:end]
    breaks = _candidate_break_offsets(
        region,
        prefer_list_breaks=prefer_list_breaks,
    )
    pieces: list[tuple[int, int, int]] = []
    cursor = 0
    while cursor < length:
        hard = min(cursor + max_chunk_chars, length)
        if hard == length:
            pieces.append((start + cursor, end, 0 if not pieces else min(overlap_chars, cursor)))
            break
        window_floor = cursor + int(max_chunk_chars * (0.5 if prefer_list_breaks else 0.7))
        break_at = _choose_break(breaks, window_floor, hard)
        if break_at is None or break_at <= cursor:
            # Whitespace fallback inside the allowed window.
            soft = region.rfind(" ", window_floor, hard)
            if soft <= cursor:
                soft = region.rfind("\n", cursor + 1, hard)
            if soft <= cursor:
                soft = region.rfind(" ", cursor + 1, hard)
            break_at = soft + 1 if soft > cursor else hard
        abs_start = start + cursor
        abs_end = start + break_at
        overlap = 0 if not pieces else min(overlap_chars, abs_end - abs_start)
        pieces.append((abs_start, abs_end, overlap))
        next_cursor = max(break_at - overlap_chars, cursor + 1)
        if next_cursor <= cursor:
            next_cursor = break_at
        cursor = next_cursor
    return pieces


def _candidate_break_offsets(region: str, *, prefer_list_breaks: bool) -> list[int]:
    offsets: list[int] = []
    if prefer_list_breaks:
        for match in re.finditer(r"\n(?=(?:[-•▪●○\*]|[\d۰-۹٠-٩]{1,3}[.\)]|[الفبپ])\s)", region):
            offsets.append(match.start() + 1)
    for index, char in enumerate(region):
        if char not in _SENTENCE_END_CHARS:
            continue
        if not _is_valid_sentence_end(region, index):
            continue
        # Break after following whitespace if present.
        break_at = index + 1
        while break_at < len(region) and region[break_at] in " \t":
            break_at += 1
        if break_at < len(region) and region[break_at] == "\n":
            break_at += 1
        offsets.append(break_at)
    for match in re.finditer(r"\n", region):
        offsets.append(match.start() + 1)
    return sorted(set(offsets))


def _choose_break(breaks: list[int], floor: int, hard: int) -> int | None:
    candidates = [pos for pos in breaks if floor <= pos <= hard]
    if candidates:
        return max(candidates)
    # Fall back to any break in the window rather than hard-cutting mid-token.
    earlier = [pos for pos in breaks if 0 < pos <= hard]
    return max(earlier) if earlier else None


def _is_valid_sentence_end(text: str, index: int) -> bool:
    char = text[index]
    if char == ".":
        prev_char = text[index - 1] if index > 0 else ""
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if prev_char.isdigit() and next_char.isdigit():
            return False
        token = _token_before_period(text, index)
        if token.lower().rstrip(".") in _ABBREVIATIONS:
            return False
        if len(token) <= 2 and token.isalpha():
            # Single/double-letter abbreviation (Dr., م.).
            return False
    # Require whitespace, newline, or EOS after the terminator.
    if index + 1 >= len(text):
        return True
    follower = text[index + 1]
    return follower.isspace()


def _token_before_period(text: str, period_index: int) -> str:
    end = period_index
    start = end
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    return text[start:end]


def _trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start] in " \t\r\n":
        start += 1
    while end > start and text[end - 1] in " \t\r\n":
        end -= 1
    return start, end
