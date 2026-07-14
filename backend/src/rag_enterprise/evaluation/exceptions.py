"""Evaluation domain exceptions."""

from __future__ import annotations

from typing import Any


class EvaluationError(Exception):
    """Base evaluation error with a stable failure code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.details = details or {}
        super().__init__(message)


class DatasetValidationError(EvaluationError):
    """Raised when a golden dataset fails schema validation."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__("dataset_invalid", message, details=details)


class DatasetNotFoundError(EvaluationError):
    def __init__(
        self,
        message: str = "dataset_not_found",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__("dataset_not_found", message, details=details)


class KnowledgeBaseUnavailableError(EvaluationError):
    def __init__(
        self,
        message: str = "kb_unavailable",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__("kb_unavailable", message, details=details)


class AggregateIncompleteError(EvaluationError):
    def __init__(
        self,
        message: str = "aggregate_incomplete",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__("aggregate_incomplete", message, details=details)
