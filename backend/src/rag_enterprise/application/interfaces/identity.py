"""Identity provider interface."""

from __future__ import annotations

import uuid
from typing import Protocol


class IdentityContext(Protocol):
    """Authenticated subject context for application services."""

    @property
    def user_id(self) -> uuid.UUID:
        """Return the authenticated user identifier."""

    @property
    def organization_id(self) -> uuid.UUID | None:
        """Return the active organization identifier when present."""

    @property
    def workspace_id(self) -> uuid.UUID | None:
        """Return the active workspace identifier when present."""


class IdentityProvider(Protocol):
    """Resolve the current authenticated identity."""

    async def get_current_identity(self) -> IdentityContext | None:
        """Return the current identity context if authenticated."""
