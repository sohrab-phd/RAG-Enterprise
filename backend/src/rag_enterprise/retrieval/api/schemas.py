"""Retrieval API request/response schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class RetrieveRequest(BaseModel):
    """POST /retrieve body."""

    model_config = ConfigDict(frozen=True)

    query: str = Field(min_length=1)
    knowledge_base_id: uuid.UUID
    document_ids: list[uuid.UUID] | None = None
    top_k: int = Field(default=8, ge=1, le=50)
    language: str | None = None


class RetrievedChunkDTO(BaseModel):
    """Retrieved chunk exposed over HTTP."""

    model_config = ConfigDict(frozen=True)

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    score: float
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    heading: str | None = None
    language: str | None = None


class RetrieveResponseDTO(BaseModel):
    """Retrieval response payload inside SuccessEnvelope."""

    model_config = ConfigDict(frozen=True)

    query: str
    knowledge_base_id: uuid.UUID
    embedding_model_id: uuid.UUID
    top_k: int
    results: list[RetrievedChunkDTO]
    result_count: int
    warnings: list[str] = Field(default_factory=list)
