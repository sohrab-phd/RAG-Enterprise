"""BGE-M3 embedding provider adapter."""

from __future__ import annotations

import asyncio
import hashlib
import math
from typing import Any, Literal

from rag_enterprise.indexing.constants import DEFAULT_DIMENSIONS, DEFAULT_MODEL_KEY
from rag_enterprise.indexing.exceptions import ModelUnavailableError


class BgeM3EmbeddingProvider:
    """EmbeddingProvider for BAAI/bge-m3.

    Modes:
    - ``deterministic``: hash-derived vectors for local/dev/tests (no model download)
    - ``flag``: FlagEmbedding BGEM3FlagModel when installed
    """

    def __init__(
        self,
        *,
        mode: Literal["deterministic", "flag"] = "deterministic",
        model_key: str = DEFAULT_MODEL_KEY,
        dimensions: int = DEFAULT_DIMENSIONS,
        query_instruction: str = "Represent this sentence for searching relevant passages: ",
    ) -> None:
        self._mode = mode
        self._model_key = model_key
        self._dimensions = dimensions
        self._query_instruction = query_instruction
        self._model: Any | None = None

    @property
    def provider_name(self) -> str:
        return self._mode

    @property
    def model_key(self) -> str:
        return self._model_key

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def is_loaded(self) -> bool:
        return self._mode == "deterministic" or self._model is not None

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._mode == "deterministic":
            return [self._deterministic_vector(text) for text in texts]
        return await asyncio.to_thread(self._flag_embed, texts, is_query=False)

    async def embed_query(self, text: str) -> list[float]:
        if self._mode == "deterministic":
            return self._deterministic_vector(f"query::{text}")
        vectors = await asyncio.to_thread(self._flag_embed, [text], is_query=True)
        return vectors[0]

    def _ensure_flag_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from FlagEmbedding import BGEM3FlagModel
        except ImportError as exc:
            raise ModelUnavailableError(
                "FlagEmbedding is not installed; install it or use deterministic mode"
            ) from exc
        try:
            self._model = BGEM3FlagModel(self._model_key, use_fp16=True)
        except Exception as exc:
            raise ModelUnavailableError(f"Failed to load embedding model: {exc}") from exc
        return self._model

    def _flag_embed(self, texts: list[str], *, is_query: bool) -> list[list[float]]:
        model = self._ensure_flag_model()
        encode = model.encode
        payload = [f"{self._query_instruction}{text}" for text in texts] if is_query else texts
        output = encode(payload)
        if isinstance(output, dict) and "dense_vecs" in output:
            dense = output["dense_vecs"]
        else:
            dense = output
        vectors = [[float(value) for value in row] for row in dense]
        for vector in vectors:
            if len(vector) != self._dimensions:
                raise ModelUnavailableError(
                    f"Model returned dimension {len(vector)}, expected {self._dimensions}"
                )
        return vectors

    def _deterministic_vector(self, text: str) -> list[float]:
        """Build a stable L2-normalized vector from SHA-256 of text."""
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        seed = digest
        while len(values) < self._dimensions:
            seed = hashlib.sha256(seed).digest()
            for offset in range(0, len(seed), 4):
                if len(values) >= self._dimensions:
                    break
                chunk = int.from_bytes(seed[offset : offset + 4], "big")
                values.append((chunk / 0xFFFFFFFF) * 2.0 - 1.0)
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]
