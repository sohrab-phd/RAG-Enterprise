"""Metadata assembly for extraction results."""

from __future__ import annotations

from rag_enterprise.processing.models import ExtractionMetadata, ParserOutput


def build_metadata(
    *,
    text: str,
    language: str,
    parser_output: ParserOutput,
    extra_warnings: list[str] | None = None,
) -> ExtractionMetadata:
    """Build extraction metadata from parser output and detected language."""
    warnings = list(parser_output.warnings)
    if extra_warnings:
        warnings.extend(extra_warnings)

    return ExtractionMetadata(
        language=language,
        character_count=len(text),
        page_count=parser_output.page_count,
        parser=parser_output.parser,
        warnings=warnings,
    )
