"""Generation request/response models and conversation enums."""

from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from rag_enterprise.retrieval.models import RetrievedChunk


class GenerationStatus(StrEnum):
    COMPLETED = "completed"
    ABSTAINED = "abstained"
    FAILED = "failed"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class MessageTurn(BaseModel):
    """Prior conversation turn for prompt history."""

    model_config = ConfigDict(frozen=True)

    role: MessageRole
    content: str


class Citation(BaseModel):
    """Evidence link from an answer to a retrieved chunk."""

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


class GenerationRequest(BaseModel):
    """Input for one grounded generation turn."""

    model_config = ConfigDict(frozen=True)

    question: str
    organization_id: uuid.UUID
    workspace_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    user_id: uuid.UUID
    permissions: frozenset[str] = frozenset()
    conversation_id: uuid.UUID | None = None
    history: list[MessageTurn] | None = None
    document_ids: list[uuid.UUID] | None = None
    language_hint: str | None = None
    top_k: int | None = None


class GenerationResult(BaseModel):
    """Outcome of RAG generation for one user turn."""

    model_config = ConfigDict(frozen=True)

    status: GenerationStatus
    answer: str | None = None
    abstention_reason: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    retrieved_chunk_ids: list[uuid.UUID] = Field(default_factory=list)
    model_key: str | None = None
    prompt_template_version: str | None = None
    conversation_id: uuid.UUID | None = None
    warnings: list[str] = Field(default_factory=list)
    failure_reason: str | None = None


class BuiltPrompt(BaseModel):
    """Prompt ready for LLMProvider.complete."""

    model_config = ConfigDict(frozen=True)

    system_prompt: str
    user_prompt: str
    template_version: str
    markers: dict[str, uuid.UUID]
    chunks_used: list[RetrievedChunk]
    history_used: list[MessageTurn]
    context_diagnostics: dict[str, object] = Field(default_factory=dict)
