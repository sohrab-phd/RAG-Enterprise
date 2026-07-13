"""Metadata filter helpers for retrieval."""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalFilters:
    """Normalized filters applied before vector ranking."""

    organization_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    embedding_model_id: uuid.UUID
    document_ids: tuple[uuid.UUID, ...] | None = None
    language: str | None = None


def build_filters(
    *,
    organization_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    embedding_model_id: uuid.UUID,
    document_ids: list[uuid.UUID] | None = None,
    language: str | None = None,
) -> RetrievalFilters:
    """Build tenant-safe retrieval filters."""
    return RetrievalFilters(
        organization_id=organization_id,
        knowledge_base_id=knowledge_base_id,
        embedding_model_id=embedding_model_id,
        document_ids=tuple(document_ids) if document_ids else None,
        language=language,
    )
