"""HTML parser."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from rag_enterprise.processing.exceptions import CorruptFileError
from rag_enterprise.processing.models import ParserOutput
from rag_enterprise.processing.parsers.text import parse_text


def parse_html(path: Path) -> ParserOutput:
    """Extract visible text from HTML."""
    parsed = parse_text(path)
    try:
        soup = BeautifulSoup(parsed.text, "html.parser")
    except Exception as exc:
        raise CorruptFileError(f"Cannot parse HTML file: {path}") from exc

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text("\n", strip=True)
    return ParserOutput(text=text, parser="html", warnings=list(parsed.warnings))
