"""Markdown parser."""

from __future__ import annotations

import re
from pathlib import Path

from rag_enterprise.processing.models import ParserOutput
from rag_enterprise.processing.parsers.text import parse_text

_HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_EMPHASIS_RE = re.compile(r"(\*\*|__|\*|_)(.*?)\1")


def parse_markdown(path: Path) -> ParserOutput:
    """Extract readable text from markdown with minimal markup removal."""
    parsed = parse_text(path)
    text = parsed.text
    text = _CODE_FENCE_RE.sub("", text)
    text = _IMAGE_RE.sub(r"\1", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _INLINE_CODE_RE.sub(r"\1", text)
    text = _EMPHASIS_RE.sub(r"\2", text)
    text = _HEADING_RE.sub("", text)
    return ParserOutput(text=text.strip(), parser="markdown", warnings=list(parsed.warnings))
