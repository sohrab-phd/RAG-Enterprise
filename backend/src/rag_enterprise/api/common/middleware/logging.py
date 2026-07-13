"""Structured HTTP request logging middleware."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from rag_enterprise.core.logging.setup import get_logger

logger = get_logger(__name__)

SendCallable = Callable[[Message], Awaitable[None]]


class RequestLoggingMiddleware:
    """Emit structured request lifecycle logs with correlation context."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")
        client = scope.get("client")
        client_host = client[0] if client else None
        started_at = time.perf_counter()
        status_code = 500

        logger.info(
            "http_request_started",
            method=method,
            path=path,
            client_host=client_host,
        )

        async def send_with_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_with_status)

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "http_request_completed",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
        )
