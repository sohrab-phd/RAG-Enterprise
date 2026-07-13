"""Indexing constants."""

from __future__ import annotations

import uuid

# Stable platform catalog ID for default BGE-M3 model (UUIDv7-style).
DEFAULT_EMBEDDING_MODEL_ID = uuid.UUID("018f0000-0000-7000-8000-00000000b6e3")
DEFAULT_MODEL_KEY = "BAAI/bge-m3"
DEFAULT_DIMENSIONS = 1024
DEFAULT_BATCH_SIZE = 32
DEFAULT_MAX_BATCH_CHARS = 50_000
DEFAULT_BATCH_TIMEOUT_SECONDS = 120.0
