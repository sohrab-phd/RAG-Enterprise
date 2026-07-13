"""Parser dispatch by file extension."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from rag_enterprise.processing.exceptions import UnsupportedFormatError
from rag_enterprise.processing.models import ParserOutput
from rag_enterprise.processing.parsers.docx import parse_docx
from rag_enterprise.processing.parsers.html import parse_html
from rag_enterprise.processing.parsers.markdown import parse_markdown
from rag_enterprise.processing.parsers.pdf import parse_pdf
from rag_enterprise.processing.parsers.text import parse_text

PARSER_BY_SUFFIX: dict[str, Callable[[Path], ParserOutput]] = {
    ".txt": parse_text,
    ".md": parse_markdown,
    ".html": parse_html,
    ".htm": parse_html,
    ".docx": parse_docx,
    ".pdf": parse_pdf,
}


def parse_file(path: Path) -> ParserOutput:
    """Select a parser based on file suffix."""
    suffix = path.suffix.lower()
    parser = PARSER_BY_SUFFIX.get(suffix)
    if parser is None:
        raise UnsupportedFormatError(f"Unsupported file format: {suffix}")
    return parser(path)
