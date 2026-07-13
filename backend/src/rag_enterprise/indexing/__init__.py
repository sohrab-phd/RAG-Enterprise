"""Indexing package for embeddings and document version indexing."""

from rag_enterprise.indexing.models import Chunk, Embedding, IndexingResult
from rag_enterprise.indexing.providers import BgeM3EmbeddingProvider
from rag_enterprise.indexing.service import IndexingService

__all__ = [
    "BgeM3EmbeddingProvider",
    "Chunk",
    "Embedding",
    "IndexingResult",
    "IndexingService",
]
