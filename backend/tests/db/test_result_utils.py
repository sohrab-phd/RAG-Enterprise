"""Unit tests for SQLAlchemy result_rowcount helper (RC3.7)."""

from __future__ import annotations

from types import SimpleNamespace

from rag_enterprise.db.result_utils import result_rowcount


def test_result_rowcount_reads_cursor_attribute() -> None:
    assert result_rowcount(SimpleNamespace(rowcount=3)) == 3


def test_result_rowcount_treats_missing_or_none_as_zero() -> None:
    assert result_rowcount(SimpleNamespace()) == 0
    assert result_rowcount(SimpleNamespace(rowcount=None)) == 0
