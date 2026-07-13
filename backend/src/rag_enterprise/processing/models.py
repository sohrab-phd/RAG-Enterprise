"""Document processing result models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExtractionMetadata(BaseModel):
    """Metadata produced during document extraction."""

    model_config = ConfigDict(frozen=True)

    language: str = Field(description="Detected language: fa, en, or unknown")
    character_count: int = Field(ge=0)
    page_count: int | None = Field(default=None, ge=0)
    parser: str = Field(description="Parser that extracted the text")
    warnings: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Final output of document processing."""

    model_config = ConfigDict(frozen=True)

    text: str
    metadata: ExtractionMetadata
    warnings: list[str] = Field(default_factory=list)


class ParserOutput(BaseModel):
    """Raw output from a format-specific parser."""

    model_config = ConfigDict(frozen=True)

    text: str
    parser: str
    page_count: int | None = None
    warnings: list[str] = Field(default_factory=list)
