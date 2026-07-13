"""Tenant scope for repository queries."""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TenantScope:
    """Workspace-scoped tenant filter."""

    organization_id: uuid.UUID
    workspace_id: uuid.UUID
