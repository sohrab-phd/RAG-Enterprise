"""Query package."""

from rag_enterprise.application.queries.base import Query, QueryBase

__all__ = ["Query", "QueryBase", "QueryDispatcher"]


def __getattr__(name: str) -> object:
    if name == "QueryDispatcher":
        from rag_enterprise.application.queries.dispatcher import QueryDispatcher

        return QueryDispatcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
