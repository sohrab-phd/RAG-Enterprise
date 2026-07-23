"""Factory for Settings-selected embedding providers (config-only model swaps)."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.application.interfaces.embedding import EmbeddingProvider
from rag_enterprise.core.config.settings import Settings
from rag_enterprise.indexing.models import Chunk, Embedding
from rag_enterprise.indexing.providers.bge_m3 import BgeM3EmbeddingProvider
from rag_enterprise.indexing.providers.sentence_transformers_provider import (
    SentenceTransformerEmbeddingProvider,
)

logger = logging.getLogger(__name__)

# Cosine floor: vectors from the same embedder on the same text should be ~1.0.
# Below this → index was almost certainly built with a different embedding path.
_INDEX_ALIGNMENT_MIN_COSINE = 0.95

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


@dataclass(frozen=True)
class EmbeddingRuntimeInfo:
    """Operator-facing embedding inventory."""

    backend: str
    provider: str
    model: str
    dimensions: int
    loaded: bool = False
    index_compatible: bool | None = None
    reindex_required: bool = False
    indexed_model_keys: tuple[str, ...] = ()
    indexed_dimensions: tuple[int, ...] = ()
    detail: str | None = None


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Build the embedding adapter from Settings — no pipeline callers change.

    There is no silent fallback between backends. The configured
    ``EMBEDDING_BACKEND`` is the exclusive selection path.
    """
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


def describe_embedding_runtime(
    settings: Settings,
    provider: EmbeddingProvider | None = None,
    *,
    index_alignment: dict[str, Any] | None = None,
) -> EmbeddingRuntimeInfo:
    """Describe the active embedding stack for inventory endpoints."""
    provider_name: str = settings.embedding_backend
    model = settings.embedding_model_key
    dimensions = settings.embedding_dimensions
    loaded = False
    if provider is not None:
        provider_name = str(getattr(provider, "provider_name", provider_name))
        model = provider.model_key
        dimensions = provider.dimensions
        loaded = bool(getattr(provider, "is_loaded", False))

    indexed_keys: tuple[str, ...] = ()
    indexed_dims: tuple[int, ...] = ()
    compatible: bool | None = None
    reindex = False
    detail: str | None = None
    if index_alignment is not None:
        indexed_keys = tuple(index_alignment.get("indexed_model_keys") or ())
        indexed_dims = tuple(index_alignment.get("indexed_dimensions") or ())
        compatible = index_alignment.get("compatible")
        reindex = bool(index_alignment.get("reindex_required"))
        detail = (
            str(index_alignment["detail"]) if index_alignment.get("detail") is not None else None
        )

    return EmbeddingRuntimeInfo(
        backend=settings.embedding_backend,
        provider=provider_name,
        model=model,
        dimensions=dimensions,
        loaded=loaded,
        index_compatible=compatible,
        reindex_required=reindex,
        indexed_model_keys=indexed_keys,
        indexed_dimensions=indexed_dims,
        detail=detail,
    )


def emit_embedding_startup_log(settings: Settings, provider: EmbeddingProvider) -> None:
    """Write the operator-facing embedding startup summary."""
    provider_name = str(getattr(provider, "provider_name", settings.embedding_backend))
    lines = [
        "--------------------------------------------",
        "Embedding Backend",
        settings.embedding_backend,
        "",
        "Embedding Provider",
        provider_name,
        "",
        "Embedding Model",
        provider.model_key,
        "",
        "Embedding Dimensions",
        str(provider.dimensions),
        "--------------------------------------------",
    ]
    logger.info("\n".join(lines))
    if settings.embedding_backend == "deterministic" and settings.app_env != "test":
        logger.warning(
            "deterministic_embeddings_active\n"
            "------------------------------------------------\n"
            "EMBEDDING_BACKEND=deterministic is active.\n"
            "This is for tests/offline demos only.\n"
            "RC2.3–RC2.5 / production retrieval requires:\n"
            "  EMBEDDING_BACKEND=sentence_transformers\n"
            "  EMBEDDING_MODEL_KEY=BAAI/bge-m3\n"
            "  EMBEDDING_DIMENSIONS=1024\n"
            "------------------------------------------------"
        )


async def probe_embedding_provider(provider: EmbeddingProvider) -> dict[str, Any]:
    """Lightweight readiness probe: load path + dimensions for one encode."""
    vector = await provider.embed_query("embedding readiness ping")
    return {
        "ok": True,
        "backend_provider": getattr(provider, "provider_name", "unknown"),
        "loaded_model": provider.model_key,
        "model_dimensions": provider.dimensions,
        "vector_dimensions": len(vector),
        "loaded": bool(getattr(provider, "is_loaded", True)),
        "detail": "ok",
    }


async def check_index_embedding_alignment(
    session_factory: async_sessionmaker[AsyncSession],
    provider: EmbeddingProvider,
    settings: Settings,
) -> dict[str, Any]:
    """Detect embeddings written by a different model/backend than the live provider.

    Stored ``model_key`` alone is insufficient (deterministic still labels BGE-M3).
    Re-embed one indexed chunk (preferring the configured model_key) and compare
    cosine similarity to the stored vector.
    """
    async with session_factory() as session:
        distinct_rows = (
            await session.execute(select(Embedding.model_key, Embedding.dimensions).distinct())
        ).all()
        indexed_model_keys = sorted({str(row[0]) for row in distinct_rows if row[0]})
        indexed_dimensions = sorted({int(row[1]) for row in distinct_rows if row[1] is not None})

        sample = (
            await session.execute(
                select(Embedding, Chunk)
                .join(Chunk, Chunk.id == Embedding.chunk_id)
                .where(Embedding.model_key == settings.embedding_model_key)
                .limit(1)
            )
        ).first()
        if sample is None:
            sample = (
                await session.execute(
                    select(Embedding, Chunk).join(Chunk, Chunk.id == Embedding.chunk_id).limit(1)
                )
            ).first()

    if not indexed_model_keys:
        return {
            "compatible": True,
            "reindex_required": False,
            "indexed_model_keys": [],
            "indexed_dimensions": [],
            "detail": "no embeddings indexed yet",
            "sample_cosine": None,
        }

    foreign_models = [key for key in indexed_model_keys if key != settings.embedding_model_key]
    missing_configured = settings.embedding_model_key not in indexed_model_keys
    dim_mismatch = any(dim != settings.embedding_dimensions for dim in indexed_dimensions)

    sample_cosine: float | None = None
    vector_mismatch = False
    if sample is not None:
        embedding_row, chunk_row = sample
        fresh = await provider.embed_texts([chunk_row.text])
        stored = list(embedding_row.vector)
        if fresh and stored:
            sample_cosine = _cosine(fresh[0], stored)
            vector_mismatch = sample_cosine < _INDEX_ALIGNMENT_MIN_COSINE

    incompatible = missing_configured or dim_mismatch or vector_mismatch
    if incompatible:
        detail = (
            "Indexed embeddings do not match the live embedding provider. "
            f"configured_model={settings.embedding_model_key!r} "
            f"configured_dimensions={settings.embedding_dimensions} "
            f"indexed_model_keys={indexed_model_keys} "
            f"indexed_dimensions={indexed_dimensions} "
            f"sample_cosine={sample_cosine}. "
            "Re-index the knowledge base (Process & Index / reindex) before relying on retrieval."
        )
        logger.warning("embedding_index_mismatch\n%s", detail)
    else:
        detail = (
            f"index aligned with live provider "
            f"(sample_cosine={sample_cosine}, models={indexed_model_keys})"
        )
        if foreign_models:
            detail += (
                f" WARNING: additional model_keys present {foreign_models}; "
                "re-index those corpora onto the configured model for uniform quality."
            )
            logger.warning("embedding_index_extra_models\n%s", detail)

    return {
        "compatible": not incompatible,
        "reindex_required": incompatible,
        "indexed_model_keys": indexed_model_keys,
        "indexed_dimensions": indexed_dimensions,
        "detail": detail,
        "sample_cosine": sample_cosine,
    }


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_l = math.sqrt(sum(a * a for a in left)) or 1e-9
    norm_r = math.sqrt(sum(b * b for b in right)) or 1e-9
    return dot / (norm_l * norm_r)
