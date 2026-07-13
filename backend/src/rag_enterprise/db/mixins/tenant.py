"""Tenant ownership mixins."""

import uuid

from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column


class OrganizationTenantMixin:
    """Organization-scoped tenant columns."""

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )


class WorkspaceTenantMixin(OrganizationTenantMixin):
    """Workspace-scoped tenant columns with denormalized organization key."""

    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)


class KnowledgeBaseTenantMixin(WorkspaceTenantMixin):
    """Knowledge-base-scoped tenant columns."""

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )


class ConversationTenantMixin(WorkspaceTenantMixin):
    """Conversation-scoped tenant columns."""

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
