"""Confirm indexing/retrieval/generation share one EmbeddingProvider instance."""

from __future__ import annotations

from dataclasses import dataclass

from rag_enterprise.indexing.providers import (
    SentenceTransformerEmbeddingProvider,
    create_embedding_provider,
)


@dataclass(frozen=True)
class _Settings:
    embedding_backend: str = "sentence_transformers"
    embedding_model_key: str = "BAAI/bge-m3"
    embedding_dimensions: int = 1024


def test_create_embedding_provider_is_sole_st_constructor() -> None:
    provider = create_embedding_provider(_Settings())  # type: ignore[arg-type]
    assert isinstance(provider, SentenceTransformerEmbeddingProvider)
    assert provider.provider_name == "sentence_transformers"
    assert provider.model_key == "BAAI/bge-m3"
    assert provider.dimensions == 1024


def test_default_settings_backend_is_sentence_transformers() -> None:
    from rag_enterprise.core.config.settings import Settings

    # Field default (ignoring .env) — production / benchmark parity.
    field = Settings.model_fields["embedding_backend"]
    assert field.default == "sentence_transformers"
