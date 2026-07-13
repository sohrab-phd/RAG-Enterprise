"""PDF parser."""

from __future__ import annotations

from pathlib import Path

import fitz

from rag_enterprise.processing.exceptions import CorruptFileError, EncryptedPdfError
from rag_enterprise.processing.models import ParserOutput


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
        for index, page in enumerate(document, start=1):
            page_text = page.get_text().strip()
            if not page_text:
                warnings.append(f"empty_page_{index}")
            else:
                parts.append(page_text)

        return ParserOutput(
            text="\n\n".join(parts),
            parser="pdf",
            page_count=document.page_count,
            warnings=warnings,
        )
    finally:
        document.close()
