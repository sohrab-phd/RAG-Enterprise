"""Document processing service."""

from __future__ import annotations

from pathlib import Path

from rag_enterprise.processing.exceptions import EmptyContentError
from rag_enterprise.processing.language import detect_language
from rag_enterprise.processing.metadata import build_metadata
from rag_enterprise.processing.models import ExtractionResult
from rag_enterprise.processing.normalization import normalize_persian_text
from rag_enterprise.processing.parsers import parse_file


class DocumentProcessingService:
    """Extract and normalize text from a local file."""

    def process_file(self, file_path: str | Path) -> ExtractionResult:
        """Process a document and return normalized extracted text."""
        path = Path(file_path)
        parser_output = parse_file(path)

        raw_text = parser_output.text.strip()
        if not raw_text:
            raise EmptyContentError(f"No extractable text in file: {path}")

        language = detect_language(raw_text)
        normalized_text = normalize_persian_text(raw_text)

        if not normalized_text.strip():
            raise EmptyContentError(f"No extractable text after normalization: {path}")

        extra_warnings: list[str] = []
        if language == "unknown":
            extra_warnings.append("language_detection_uncertain")

        metadata = build_metadata(
            text=normalized_text,
            language=language,
            parser_output=parser_output,
            extra_warnings=extra_warnings,
        )

        return ExtractionResult(
            text=normalized_text,
            metadata=metadata,
            warnings=list(metadata.warnings),
        )
