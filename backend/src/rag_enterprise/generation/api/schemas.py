"""Chat API schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from rag_enterprise.retrieval.api.schemas import RetrievedChunkDTO


class ChatRequest(BaseModel):
    """POST /chat body."""

    model_config = ConfigDict(frozen=True)

    question: str = Field(min_length=1)
    knowledge_base_id: uuid.UUID
    conversation_id: uuid.UUID | None = None
    document_ids: list[uuid.UUID] | None = None
    top_k: int | None = Field(default=None, ge=1, le=50)
    language_hint: str | None = None


class CitationDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    rank: int
    relevance_score: float
    excerpt: str
    start_char: int | None = None
    end_char: int | None = None
    marker: str


class ChatResponseDTO(BaseModel):
    """Chat response inside SuccessEnvelope."""

    model_config = ConfigDict(frozen=True)

    conversation_id: uuid.UUID | None
    answer: str | None
    citations: list[CitationDTO]
    retrieved_chunks: list[RetrievedChunkDTO]
    abstained: bool
    status: str
    abstention_reason: str | None = None
    failure_reason: str | None = None
    model_key: str | None = None
    prompt_template_version: str | None = None
    warnings: list[str] = Field(default_factory=list)
