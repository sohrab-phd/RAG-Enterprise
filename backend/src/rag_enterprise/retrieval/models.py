"""Retrieval request and response models."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    """Input for dense vector retrieval."""

    model_config = ConfigDict(frozen=True)

    query_text: str
    organization_id: uuid.UUID
    workspace_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    top_k: int = Field(default=8, ge=1, le=50)
    document_ids: list[uuid.UUID] | None = None
    language: str | None = None
    embedding_model_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    permissions: frozenset[str] = frozenset()


class RetrievedChunk(BaseModel):
    """Single ranked retrieval result."""

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


class SearchResponse(BaseModel):
    """Envelope returned by RetrievalService.retrieve()."""

    model_config = ConfigDict(frozen=True)

    query_text: str
    knowledge_base_id: uuid.UUID
    embedding_model_id: uuid.UUID
    top_k: int
    results: list[RetrievedChunk]
    result_count: int
    warnings: list[str] = Field(default_factory=list)
