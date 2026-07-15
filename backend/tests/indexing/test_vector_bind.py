"""Regression tests for EmbeddingVector bind handling and cosine distance SQL."""

from __future__ import annotations

import pytest
from sqlalchemy import Float, bindparam, select
from sqlalchemy.dialects import postgresql

from rag_enterprise.db.types.vector import EmbeddingVector
from rag_enterprise.indexing.models import Embedding


def test_embedding_vector_rejects_non_sequence_bind() -> None:
    column_type = EmbeddingVector(dimensions=3)
    with pytest.raises(TypeError, match="sequence of floats"):
        column_type.process_bind_param(1, dialect=postgresql.dialect())  # type: ignore[arg-type]


def test_postgresql_distance_expression_does_not_subtract_literal_one() -> None:
    """Chat failed when SQL used `1 - (vector <=> q)` and typed `1` as a Vector bind."""
    query_vector = [0.0] * 1024
    distance = Embedding.vector.op("<=>", return_type=Float())(
        bindparam("query_vector", value=query_vector)
    )
    statement = select(Embedding.id, distance.label("distance")).limit(5)
    compiled = str(statement.compile(dialect=postgresql.dialect()))
    assert "<=>" in compiled
    assert "1 -" not in compiled.replace(" ", "")
    assert "1-" not in compiled.replace(" ", "")
