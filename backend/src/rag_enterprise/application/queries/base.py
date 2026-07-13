"""Query abstractions."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


@runtime_checkable
class Query(Protocol):
    """Marker protocol for read-side application queries."""


class QueryBase(BaseModel):
    """Base class for read-only queries."""

    model_config = ConfigDict(frozen=True, extra="forbid")
