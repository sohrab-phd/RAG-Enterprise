"""Conversation and message tables for RAG chat history."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_conversation_messages"
down_revision: str | None = "002_embeddings_indexing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_base_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_base.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversation_organization_id", "conversation", ["organization_id"])
    op.create_index("ix_conversation_workspace_id", "conversation", ["workspace_id"])
    op.create_index("ix_conversation_user_id", "conversation", ["user_id"])
    op.create_index("ix_conversation_knowledge_base_id", "conversation", ["knowledge_base_id"])

    op.create_table(
        "message",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_base_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("generation_status", sa.String(length=32), nullable=True),
        sa.Column("abstention_reason", sa.String(length=64), nullable=True),
        sa.Column("model_key", sa.String(length=128), nullable=True),
        sa.Column("prompt_template_version", sa.String(length=32), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversation.id"]),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_base.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_message_organization_id", "message", ["organization_id"])
    op.create_index("ix_message_workspace_id", "message", ["workspace_id"])
    op.create_index("ix_message_conversation_id", "message", ["conversation_id"])
    op.create_index("ix_message_knowledge_base_id", "message", ["knowledge_base_id"])


def downgrade() -> None:
    op.drop_table("message")
    op.drop_table("conversation")
