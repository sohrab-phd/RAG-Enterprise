"""Retrieval exceptions."""

from __future__ import annotations


class RetrievalError(Exception):
    """Base retrieval error with stable code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class InvalidQueryError(RetrievalError):
    def __init__(self, message: str = "Query text is empty") -> None:
        super().__init__("invalid_query", message)


class ForbiddenRetrievalError(RetrievalError):
    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__("forbidden", message)


class KnowledgeBaseNotFoundError(RetrievalError):
    def __init__(self, message: str = "Knowledge base not found") -> None:
        super().__init__("knowledge_base_not_found", message)


class KnowledgeBaseUnavailableError(RetrievalError):
    def __init__(self, message: str = "Knowledge base is not searchable") -> None:
        super().__init__("knowledge_base_unavailable", message)


class ModelMismatchError(RetrievalError):
    def __init__(self, message: str = "Requested embedding model does not match index") -> None:
        super().__init__("model_mismatch", message)
