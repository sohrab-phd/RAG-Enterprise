"""Factory for Settings-selected embedding providers (config-only model swaps)."""

from __future__ import annotations

from typing import Any

from rag_enterprise.application.interfaces.embedding import EmbeddingProvider
from rag_enterprise.core.config.settings import Settings
from rag_enterprise.indexing.providers.bge_m3 import BgeM3EmbeddingProvider
from rag_enterprise.indexing.providers.sentence_transformers_provider import (
    SentenceTransformerEmbeddingProvider,
)

# Known retrieval-model encoding conventions. Unknown keys use empty prefixes.
_MODEL_PROFILES: dict[str, dict[str, Any]] = {
    "BAAI/bge-m3": {
        "query_prefix": "",
        "passage_prefix": "",
        "trust_remote_code": False,
        "query_encode_kwargs": {},
        "encode_kwargs": {},
    },
    "intfloat/multilingual-e5-large": {
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
        "trust_remote_code": False,
    },
    "intfloat/multilingual-e5-base": {
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
        "trust_remote_code": False,
    },
    "jinaai/jina-embeddings-v3": {
        "query_prefix": "",
        "passage_prefix": "",
        "trust_remote_code": True,
        "query_encode_kwargs": {"task": "retrieval.query"},
        "encode_kwargs": {"task": "retrieval.passage"},
    },
    "Snowflake/snowflake-arctic-embed-l-v2.0": {
        "query_prefix": "",
        "passage_prefix": "",
        "trust_remote_code": False,
        "query_encode_kwargs": {"prompt_name": "query"},
        "encode_kwargs": {},
    },
}


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Build the embedding adapter from Settings — no pipeline callers change."""
    backend = settings.embedding_backend
    model_key = settings.embedding_model_key
    dimensions = settings.embedding_dimensions

    if backend == "deterministic":
        return BgeM3EmbeddingProvider(
            mode="deterministic",
            model_key=model_key,
            dimensions=dimensions,
        )
    if backend == "flag":
        return BgeM3EmbeddingProvider(
            mode="flag",
            model_key=model_key,
            dimensions=dimensions,
        )
    if backend == "sentence_transformers":
        profile = _MODEL_PROFILES.get(model_key, {})
        return SentenceTransformerEmbeddingProvider(
            model_key=model_key,
            dimensions=dimensions,
            query_prefix=str(profile.get("query_prefix", "")),
            passage_prefix=str(profile.get("passage_prefix", "")),
            trust_remote_code=bool(profile.get("trust_remote_code", False)),
            encode_kwargs=dict(profile.get("encode_kwargs") or {}),
            query_encode_kwargs=dict(profile.get("query_encode_kwargs") or {}),
        )
    raise ValueError(f"Unsupported embedding backend: {backend!r}")
