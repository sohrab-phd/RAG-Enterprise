"""Global API exception handlers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from rag_enterprise.api.common.context import CORRELATION_ID_HEADER, REQUEST_ID_HEADER
from rag_enterprise.api.common.errors import (
    ApplicationException,
    ErrorEnvelope,
    UnexpectedError,
    error_response,
    from_application_error,
)
from rag_enterprise.application.common.errors import ErrorCode
from rag_enterprise.core.logging.setup import get_logger

logger = get_logger(__name__)


def _response_headers(request: Request) -> dict[str, str]:
    headers: dict[str, str] = {}
    request_id = getattr(request.state, "request_id", None)
    correlation_id = getattr(request.state, "correlation_id", None)
    if request_id:
        headers[REQUEST_ID_HEADER] = request_id
    if correlation_id:
        headers[CORRELATION_ID_HEADER] = correlation_id
    return headers


def _json_error_response(
    request: Request,
    *,
    status_code: int,
    envelope: ErrorEnvelope,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(mode="json"),
        headers=_response_headers(request),
    )


async def handle_request_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Translate request validation failures into the standard error envelope."""
    envelope = error_response(
        code=ErrorCode.VALIDATION_FAILED,
        message="Request validation failed",
        details={"errors": exc.errors()},
    )
    return _json_error_response(request, status_code=422, envelope=envelope)


async def handle_application_exception(
    request: Request,
    exc: ApplicationException,
) -> JSONResponse:
    """Translate application errors into the standard error envelope."""
    envelope, status_code = from_application_error(exc.error)
    return _json_error_response(request, status_code=status_code, envelope=envelope)


async def handle_unexpected_error(
    request: Request,
    exc: UnexpectedError,
) -> JSONResponse:
    """Translate unexpected API errors into a safe client response."""
    logger.exception(
        "unexpected_api_error",
        path=request.url.path,
        method=request.method,
        error_message=exc.message,
    )
    envelope = error_response(
        code=ErrorCode.INTERNAL_ERROR,
        message=exc.message,
        details=exc.details or None,
    )
    return _json_error_response(request, status_code=500, envelope=envelope)


async def handle_uncaught_exception(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Translate uncaught exceptions into a safe internal error response."""
    logger.exception(
        "uncaught_exception",
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
    )
    envelope = error_response(
        code=ErrorCode.INTERNAL_ERROR,
        message="An unexpected error occurred",
    )
    return _json_error_response(request, status_code=500, envelope=envelope)


async def handle_http_exception(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Normalize Starlette HTTP exceptions into the standard error envelope."""
    code = _http_status_to_error_code(exc.status_code)
    details: dict[str, Any] | None = None
    if isinstance(exc.detail, dict):
        details = exc.detail
    elif isinstance(exc.detail, list):
        details = {"errors": exc.detail}
    elif exc.detail:
        details = {"detail": exc.detail}

    envelope = error_response(
        code=code,
        message=_http_status_message(exc.status_code, exc.detail),
        details=details,
    )
    return _json_error_response(
        request,
        status_code=exc.status_code,
        envelope=envelope,
    )


def _http_status_to_error_code(status_code: int) -> str:
    mapping = {
        400: ErrorCode.VALIDATION_FAILED,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        409: ErrorCode.CONFLICT,
        422: ErrorCode.VALIDATION_FAILED,
    }
    return mapping.get(status_code, ErrorCode.INTERNAL_ERROR)


def _http_status_message(status_code: int, detail: Any) -> str:
    if isinstance(detail, str):
        return detail
    return {
        400: "Bad request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not found",
        409: "Conflict",
        422: "Request validation failed",
    }.get(status_code, "Request failed")


def register_exception_handlers(app: FastAPI) -> None:
    """Register global API exception handlers."""
    handlers: list[tuple[type[Exception], Callable[..., Any]]] = [
        (RequestValidationError, handle_request_validation_error),
        (ApplicationException, handle_application_exception),
        (UnexpectedError, handle_unexpected_error),
        (StarletteHTTPException, handle_http_exception),
        (Exception, handle_uncaught_exception),
    ]
    for exc_type, handler in handlers:
        app.add_exception_handler(exc_type, handler)
