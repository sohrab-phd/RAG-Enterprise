"""Unit tests for configurable embedding provider factory."""

from __future__ import annotations

from dataclasses import dataclass

from rag_enterprise.indexing.providers import (
    BgeM3EmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
    create_embedding_provider,
)


@dataclass(frozen=True)
class _EmbeddingSettings:
    embedding_backend: str
    embedding_model_key: str
    embedding_dimensions: int = 1024


def test_factory_deterministic_backend() -> None:
    provider = create_embedding_provider(
        _EmbeddingSettings(  # type: ignore[arg-type]
            embedding_backend="deterministic",
            embedding_model_key="BAAI/bge-m3",
            embedding_dimensions=1024,
        )
    )
    assert isinstance(provider, BgeM3EmbeddingProvider)
    assert provider.model_key == "BAAI/bge-m3"
    assert provider.dimensions == 1024


def test_factory_sentence_transformers_backend() -> None:
    provider = create_embedding_provider(
        _EmbeddingSettings(  # type: ignore[arg-type]
            embedding_backend="sentence_transformers",
            embedding_model_key="intfloat/multilingual-e5-large",
            embedding_dimensions=1024,
        )
    )
    assert isinstance(provider, SentenceTransformerEmbeddingProvider)
    assert provider.model_key == "intfloat/multilingual-e5-large"
    assert provider.provider_name == "sentence_transformers"


def test_factory_deterministic_exposes_provider_name() -> None:
    provider = create_embedding_provider(
        _EmbeddingSettings(  # type: ignore[arg-type]
            embedding_backend="deterministic",
            embedding_model_key="BAAI/bge-m3",
        )
    )
    assert isinstance(provider, BgeM3EmbeddingProvider)
    assert provider.provider_name == "deterministic"


def test_model_swap_is_settings_only() -> None:
    left = create_embedding_provider(
        _EmbeddingSettings(  # type: ignore[arg-type]
            embedding_backend="deterministic",
            embedding_model_key="BAAI/bge-m3",
        )
    )
    right = create_embedding_provider(
        _EmbeddingSettings(  # type: ignore[arg-type]
            embedding_backend="deterministic",
            embedding_model_key="intfloat/multilingual-e5-large",
        )
    )
    assert left.model_key != right.model_key
    assert left.dimensions == right.dimensions == 1024
