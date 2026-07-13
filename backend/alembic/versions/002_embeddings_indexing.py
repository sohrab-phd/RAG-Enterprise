"""Chunk and embedding schema with pgvector support."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_embeddings_indexing"
down_revision: str | None = "001_initial_knowledge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        from pgvector.sqlalchemy import Vector

        vector_type: sa.types.TypeEngine[object] = Vector(1024)
    else:
        vector_type = sa.JSON()

    op.create_table(
        "chunk",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_base_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(length=500), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("strategy", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("chunking_profile", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"]),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_version.id"]),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_base.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_version_id",
            "sequence_number",
            name="uq_chunk_version_sequence",
        ),
    )
    op.create_index("ix_chunk_organization_id", "chunk", ["organization_id"])
    op.create_index("ix_chunk_workspace_id", "chunk", ["workspace_id"])
    op.create_index("ix_chunk_knowledge_base_id", "chunk", ["knowledge_base_id"])
    op.create_index("ix_chunk_document_id", "chunk", ["document_id"])
    op.create_index("ix_chunk_document_version_id", "chunk", ["document_version_id"])
    op.create_index("ix_chunk_content_hash", "chunk", ["content_hash"])
    op.create_index(
        "ix_chunk_kb_status_language",
        "chunk",
        ["knowledge_base_id", "status", "language"],
    )
    op.create_index(
        "ix_chunk_org_kb_status",
        "chunk",
        ["organization_id", "knowledge_base_id", "status"],
    )

    op.create_table(
        "embedding",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_base_id", sa.Uuid(), nullable=False),
        sa.Column("embedding_model_id", sa.Uuid(), nullable=False),
        sa.Column("model_key", sa.String(length=128), nullable=False),
        sa.Column("vector", vector_type, nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("index_status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunk.id"]),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_version.id"]),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_base.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "chunk_id",
            "embedding_model_id",
            "generation",
            name="uq_embedding_chunk_model_generation",
        ),
    )
    op.create_index("ix_embedding_organization_id", "embedding", ["organization_id"])
    op.create_index("ix_embedding_workspace_id", "embedding", ["workspace_id"])
    op.create_index("ix_embedding_chunk_id", "embedding", ["chunk_id"])
    op.create_index("ix_embedding_document_version_id", "embedding", ["document_version_id"])
    op.create_index("ix_embedding_knowledge_base_id", "embedding", ["knowledge_base_id"])
    op.create_index("ix_embedding_embedding_model_id", "embedding", ["embedding_model_id"])
    op.create_index(
        "ix_embedding_kb_model_status",
        "embedding",
        ["knowledge_base_id", "embedding_model_id", "index_status"],
    )
    op.create_index(
        "ix_embedding_org_status_created",
        "embedding",
        ["organization_id", "index_status", "created_at"],
    )

    if is_postgres:
        op.execute(
            """
            CREATE INDEX ix_embedding_hnsw_cosine
            ON embedding
            USING hnsw (vector vector_cosine_ops)
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_embedding_hnsw_cosine")
    op.drop_table("embedding")
    op.drop_table("chunk")
