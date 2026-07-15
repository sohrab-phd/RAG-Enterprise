"""Sentence-Transformers embedding provider for configurable HF retrieval models."""

from __future__ import annotations

import asyncio
from typing import Any

from rag_enterprise.indexing.exceptions import ModelUnavailableError


class SentenceTransformerEmbeddingProvider:
    """EmbeddingProvider backed by ``sentence-transformers``.

    Model selection is configuration-only (``model_key`` / ``dimensions`` / prefixes).
    The ``EmbeddingProvider`` protocol surface is unchanged.
    """

    def __init__(
        self,
        *,
        model_key: str,
        dimensions: int = 1024,
        query_prefix: str = "",
        passage_prefix: str = "",
        trust_remote_code: bool = False,
        encode_kwargs: dict[str, Any] | None = None,
        query_encode_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self._model_key = model_key
        self._dimensions = dimensions
        self._query_prefix = query_prefix
        self._passage_prefix = passage_prefix
        self._trust_remote_code = trust_remote_code
        self._encode_kwargs = dict(encode_kwargs or {})
        self._query_encode_kwargs = dict(query_encode_kwargs or {})
        self._model: Any | None = None

    @property
    def model_key(self) -> str:
        return self._model_key

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = [f"{self._passage_prefix}{text}" for text in texts]
        return await asyncio.to_thread(self._encode, payload, is_query=False)

    async def embed_query(self, text: str) -> list[float]:
        payload = [f"{self._query_prefix}{text}"]
        vectors = await asyncio.to_thread(self._encode, payload, is_query=True)
        return vectors[0]

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ModelUnavailableError(
                "sentence-transformers is not installed; install with: uv sync --extra embeddings"
            ) from exc
        try:
            self._model = SentenceTransformer(
                self._model_key,
                trust_remote_code=self._trust_remote_code,
            )
        except Exception as exc:
            raise ModelUnavailableError(f"Failed to load embedding model: {exc}") from exc
        return self._model

    def _encode(self, texts: list[str], *, is_query: bool) -> list[list[float]]:
        model = self._ensure_model()
        kwargs = dict(self._query_encode_kwargs if is_query else self._encode_kwargs)
        kwargs.setdefault("normalize_embeddings", True)
        try:
            output = model.encode(texts, **kwargs)
        except TypeError:
            # Some models reject unknown kwargs (e.g. task=).
            kwargs.pop("task", None)
            kwargs.pop("prompt_name", None)
            output = model.encode(texts, **kwargs)
        vectors = [[float(value) for value in row] for row in output]
        for vector in vectors:
            if len(vector) != self._dimensions:
                # Allow Matryoshka / truncate to configured store width when larger.
                if len(vector) > self._dimensions:
                    vector[:] = vector[: self._dimensions]
                    # Re-L2 normalize after truncate.
                    norm = sum(v * v for v in vector) ** 0.5 or 1.0
                    vector[:] = [v / norm for v in vector]
                else:
                    raise ModelUnavailableError(
                        f"Model returned dimension {len(vector)}, expected {self._dimensions}"
                    )
        return vectors
