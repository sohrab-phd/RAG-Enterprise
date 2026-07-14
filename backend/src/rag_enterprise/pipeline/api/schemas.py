"""Process-and-index API schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProcessAndIndexResponseDTO(BaseModel):
    """Result of synchronous process & index."""

    model_config = ConfigDict(frozen=True)

    current_status: str
    processed_chunks: int = Field(ge=0)
    indexed_embeddings: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)
    document_version_id: str | None = None
