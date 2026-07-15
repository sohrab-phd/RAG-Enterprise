"""Embedding provider package."""

from rag_enterprise.indexing.providers.bge_m3 import BgeM3EmbeddingProvider
from rag_enterprise.indexing.providers.factory import create_embedding_provider
from rag_enterprise.indexing.providers.sentence_transformers_provider import (
    SentenceTransformerEmbeddingProvider,
)

__all__ = [
    "BgeM3EmbeddingProvider",
    "SentenceTransformerEmbeddingProvider",
    "create_embedding_provider",
]
