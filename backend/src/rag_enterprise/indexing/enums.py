"""Indexing package enums."""

from enum import StrEnum


class ChunkStatus(StrEnum):
    CREATED = "created"
    EMBEDDED = "embedded"
    INDEXED = "indexed"
    SUPERSEDED = "superseded"
    DELETED = "deleted"


class IndexStatus(StrEnum):
    PENDING = "pending"
    INDEXED = "indexed"
    STALE = "stale"
    DELETED = "deleted"
