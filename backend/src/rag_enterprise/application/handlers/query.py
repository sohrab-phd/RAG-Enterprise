"""Query handler abstractions."""

from __future__ import annotations

from typing import Protocol, TypeVar

from rag_enterprise.application.common import Result
from rag_enterprise.application.queries.base import Query

Q = TypeVar("Q", bound=Query, contravariant=True)
R = TypeVar("R")


class QueryHandler(Protocol[Q, R]):
    """Handle a read-only query and return a typed Result."""

    async def handle(self, query: Q) -> Result[R]:
        """Execute the query."""
