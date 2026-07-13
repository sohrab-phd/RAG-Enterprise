"""Vector column type for embeddings (pgvector on Postgres, JSON elsewhere)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.engine import Dialect


class EmbeddingVector(TypeDecorator[list[float]]):
    """Store float vectors; use pgvector on PostgreSQL and JSON elsewhere."""

    impl = JSON
    cache_ok = True

    def __init__(self, dimensions: int) -> None:
        super().__init__()
        self.dimensions = dimensions

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(self.dimensions))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: list[float] | None, dialect: Dialect) -> Any:
        if value is None:
            return None
        if len(value) != self.dimensions:
            raise ValueError(f"Expected vector length {self.dimensions}, got {len(value)}")
        return list(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> list[float] | None:
        if value is None:
            return None
        return [float(item) for item in value]
