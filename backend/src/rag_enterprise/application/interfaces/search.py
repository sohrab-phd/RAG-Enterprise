"""Search provider interface."""

from __future__ import annotations

import uuid
from typing import Protocol


class SearchResult(Protocol):
    """Single retrieval candidate from a search provider."""

    @property
    def chunk_id(self) -> uuid.UUID:
        """Return the matched chunk identifier."""

    @property
    def score(self) -> float:
        """Return the relevance score."""

    @property
    def excerpt(self) -> str:
        """Return the matched text excerpt."""


class SearchProvider(Protocol):
    """Retrieve candidate chunks for a query."""

    async def search(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        query_text: str,
        top_k: int,
    ) -> list[SearchResult]:
        """Return ranked retrieval candidates."""
