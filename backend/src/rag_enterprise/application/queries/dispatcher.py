"""Query dispatcher."""

from __future__ import annotations

from typing import TypeVar, cast

from rag_enterprise.application.common import ApplicationError, ErrorCode, Result
from rag_enterprise.application.handlers.query import QueryHandler
from rag_enterprise.application.queries.base import Query

Q = TypeVar("Q", bound=Query)
R = TypeVar("R")


class QueryDispatcher:
    """Lightweight in-process query dispatcher."""

    def __init__(self) -> None:
        self._handlers: dict[type[Query], QueryHandler[Query, object]] = {}

    def register(self, query_type: type[Q], handler: QueryHandler[Q, R]) -> None:
        """Register a handler for a query type."""
        if query_type in self._handlers:
            raise ValueError(f"Handler already registered for {query_type.__name__}")
        self._handlers[query_type] = handler  # type: ignore[assignment]

    def is_registered(self, query_type: type[Query]) -> bool:
        """Return whether a handler is registered for the query type."""
        return query_type in self._handlers

    async def dispatch(self, query: Q) -> Result[R]:
        """Dispatch a read-only query to its handler."""
        handler = self._handlers.get(type(query))
        if handler is None:
            return Result.fail(
                ApplicationError(
                    code=ErrorCode.HANDLER_NOT_FOUND,
                    message=f"No handler registered for {type(query).__name__}",
                )
            )

        return cast(Result[R], await handler.handle(query))
