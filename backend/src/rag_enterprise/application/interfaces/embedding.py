"""Embedding provider interface."""

from __future__ import annotations

from typing import Protocol


class EmbeddingProvider(Protocol):
    """Generate vector embeddings for text chunks."""

    @property
    def model_key(self) -> str:
        """Return the provider model identifier."""

    @property
    def dimensions(self) -> int:
        """Return the embedding vector dimensions."""

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
