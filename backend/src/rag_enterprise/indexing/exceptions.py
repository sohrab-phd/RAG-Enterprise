"""Indexing domain exceptions."""

from __future__ import annotations


class IndexingError(Exception):
    """Base indexing error with a stable failure code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class EmptyChunkListError(IndexingError):
    def __init__(self, message: str = "Zero chunks supplied") -> None:
        super().__init__("empty_chunk_list", message)


class ModelUnavailableError(IndexingError):
    def __init__(self, message: str) -> None:
        super().__init__("model_unavailable", message)


class EmbeddingTimeoutError(IndexingError):
    def __init__(self, message: str) -> None:
        super().__init__("embedding_timeout", message)


class DimensionMismatchError(IndexingError):
    def __init__(self, message: str) -> None:
        super().__init__("dimension_mismatch", message)


class PartialEmbeddingFailureError(IndexingError):
    def __init__(self, message: str) -> None:
        super().__init__("partial_embedding_failure", message)


class StorageWriteError(IndexingError):
    def __init__(self, message: str) -> None:
        super().__init__("storage_write_error", message)
