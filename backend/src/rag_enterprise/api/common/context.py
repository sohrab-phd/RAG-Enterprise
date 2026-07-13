"""Request-scoped context for API correlation identifiers."""

from __future__ import annotations

import contextvars

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id",
    default=None,
)
correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id",
    default=None,
)


def get_request_id() -> str | None:
    """Return the current request identifier, if set."""
    return request_id_var.get()


def get_correlation_id() -> str | None:
    """Return the current correlation identifier, if set."""
    return correlation_id_var.get()
