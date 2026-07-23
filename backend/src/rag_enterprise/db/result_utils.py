"""Typed helpers for SQLAlchemy result metadata."""

from __future__ import annotations


def result_rowcount(result: object) -> int:
    """Return ``CursorResult.rowcount`` without fighting SQLAlchemy stubs."""
    return int(getattr(result, "rowcount", 0) or 0)
