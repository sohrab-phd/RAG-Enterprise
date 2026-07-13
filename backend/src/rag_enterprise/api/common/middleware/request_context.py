"""Request and correlation identifier middleware."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable, MutableMapping

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from rag_enterprise.api.common.context import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    correlation_id_var,
    request_id_var,
)

ScopeState = MutableMapping[str, object]
SendCallable = Callable[[Message], Awaitable[None]]


class RequestContextMiddleware:
    """Assign request and correlation identifiers for each HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        request_id = _get_header(headers, REQUEST_ID_HEADER) or str(uuid.uuid4())
        correlation_id = _get_header(headers, CORRELATION_ID_HEADER) or request_id

        request_id_token = request_id_var.set(request_id)
        correlation_id_token = correlation_id_var.set(correlation_id)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            correlation_id=correlation_id,
        )

        state = scope.setdefault("state", {})
        if isinstance(state, dict):
            state["request_id"] = request_id
            state["correlation_id"] = correlation_id

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((REQUEST_ID_HEADER.lower().encode(), request_id.encode()))
                headers.append(
                    (CORRELATION_ID_HEADER.lower().encode(), correlation_id.encode()),
                )
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            request_id_var.reset(request_id_token)
            correlation_id_var.reset(correlation_id_token)
            structlog.contextvars.clear_contextvars()


def _get_header(headers: dict[bytes, bytes], name: str) -> str | None:
    value = headers.get(name.lower().encode())
    if value is None:
        return None
    return value.decode()
