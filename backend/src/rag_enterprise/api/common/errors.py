"""Standard API error models and exceptions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from rag_enterprise.application.common.errors import ApplicationError, ErrorCode

ERROR_STATUS_MAP: dict[str, int] = {
    ErrorCode.VALIDATION_FAILED: 422,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.HANDLER_NOT_FOUND: 500,
    ErrorCode.INTERNAL_ERROR: 500,
}


class ErrorDetail(BaseModel):
    """Structured error payload returned to API clients."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(description="Stable machine-readable error code")
    message: str = Field(description="Human-readable error message")
    details: dict[str, Any] | list[Any] | None = Field(
        default=None,
        description="Optional structured error details",
    )


class ErrorEnvelope(BaseModel):
    """Standard error response wrapper."""

    model_config = ConfigDict(frozen=True)

    success: Literal[False] = False
    error: ErrorDetail


class ApplicationException(Exception):
    """Raised when an application error should be translated to an HTTP response."""

    def __init__(self, error: ApplicationError) -> None:
        self.error = error
        super().__init__(error.message)


class UnexpectedError(Exception):
    """Raised when an unexpected failure must be surfaced as a safe API response."""

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


def error_response(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | list[Any] | None = None,
) -> ErrorEnvelope:
    """Build a standard error envelope."""
    return ErrorEnvelope(error=ErrorDetail(code=code, message=message, details=details))


def status_code_for_error(code: str) -> int:
    """Map an application error code to an HTTP status code."""
    return ERROR_STATUS_MAP.get(code, 400)


def from_application_error(error: ApplicationError) -> tuple[ErrorEnvelope, int]:
    """Translate an application error into an API response envelope and status code."""
    envelope = error_response(
        code=error.code,
        message=error.message,
        details=error.details or None,
    )
    return envelope, status_code_for_error(error.code)
