"""Plain text parser."""

from __future__ import annotations

from pathlib import Path

from rag_enterprise.processing.exceptions import CorruptFileError
from rag_enterprise.processing.models import ParserOutput


def parse_text(path: Path) -> ParserOutput:
    """Read UTF-8 or UTF-16 text files."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise CorruptFileError(f"Cannot read text file: {path}") from exc

    for encoding in ("utf-8-sig", "utf-16", "utf-8"):
        try:
            text = raw.decode(encoding)
            return ParserOutput(text=text, parser="text")
        except UnicodeDecodeError:
            continue

    raise CorruptFileError(f"Unsupported text encoding: {path}")
