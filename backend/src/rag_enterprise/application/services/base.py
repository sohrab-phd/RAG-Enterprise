"""Application service base classes."""

from __future__ import annotations

from rag_enterprise.application.commands.dispatcher import CommandDispatcher
from rag_enterprise.application.queries.dispatcher import QueryDispatcher


class ApplicationService:
    """Base class for application services coordinating use cases."""

    def __init__(
        self,
        *,
        command_dispatcher: CommandDispatcher,
        query_dispatcher: QueryDispatcher,
    ) -> None:
        self._command_dispatcher = command_dispatcher
        self._query_dispatcher = query_dispatcher

    @property
    def commands(self) -> CommandDispatcher:
        return self._command_dispatcher

    @property
    def queries(self) -> QueryDispatcher:
        return self._query_dispatcher


class ReadApplicationService:
    """Base class for read-only application services."""

    def __init__(self, *, query_dispatcher: QueryDispatcher) -> None:
        self._query_dispatcher = query_dispatcher

    @property
    def queries(self) -> QueryDispatcher:
        return self._query_dispatcher


class WriteApplicationService:
    """Base class for write-side application services."""

    def __init__(self, *, command_dispatcher: CommandDispatcher) -> None:
        self._command_dispatcher = command_dispatcher

    @property
    def commands(self) -> CommandDispatcher:
        return self._command_dispatcher
