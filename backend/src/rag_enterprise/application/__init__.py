"""Application layer infrastructure."""

from rag_enterprise.application.commands.base import Command
from rag_enterprise.application.common.errors import ApplicationError
from rag_enterprise.application.common.result import Result
from rag_enterprise.application.events.base import DomainEvent
from rag_enterprise.application.queries.base import Query

__all__ = [
    "ApplicationError",
    "Command",
    "CommandDispatcher",
    "DomainEvent",
    "Query",
    "QueryDispatcher",
    "Result",
]


def __getattr__(name: str) -> object:
    if name == "CommandDispatcher":
        from rag_enterprise.application.commands.dispatcher import CommandDispatcher

        return CommandDispatcher
    if name == "QueryDispatcher":
        from rag_enterprise.application.queries.dispatcher import QueryDispatcher

        return QueryDispatcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
