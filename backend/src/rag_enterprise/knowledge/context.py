"""Request actor context for authorization."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RequestActor:
    """Authenticated subject for a knowledge management operation."""

    user_id: uuid.UUID
    organization_id: uuid.UUID
    permissions: frozenset[str] = field(default_factory=frozenset)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions
