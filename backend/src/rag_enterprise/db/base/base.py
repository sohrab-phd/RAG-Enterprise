"""Declarative SQLAlchemy base."""

from sqlalchemy.orm import DeclarativeBase

from rag_enterprise.db.base.metadata import metadata


class ModelBase(DeclarativeBase):
    """Base class for all ORM models."""

    metadata = metadata
