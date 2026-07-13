"""Application-layer error types."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ApplicationError:
    """Structured application error returned through the Result pattern."""

    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class ErrorCode:
    """Canonical application error codes for infrastructure flows."""

    VALIDATION_FAILED = "validation_failed"
    HANDLER_NOT_FOUND = "handler_not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    INTERNAL_ERROR = "internal_error"
