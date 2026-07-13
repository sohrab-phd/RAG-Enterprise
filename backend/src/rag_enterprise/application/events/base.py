"""Domain event abstractions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from rag_enterprise.db.types import generate_uuid7


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Base class for in-process domain events."""

    event_type: str
    aggregate_type: str
    aggregate_id: uuid.UUID
    organization_id: uuid.UUID | None = None
    workspace_id: uuid.UUID | None = None
    correlation_id: uuid.UUID | None = None
    causation_id: uuid.UUID | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1
    event_id: uuid.UUID = field(default_factory=generate_uuid7)
    occurred_at: datetime = field(default_factory=utc_now)
