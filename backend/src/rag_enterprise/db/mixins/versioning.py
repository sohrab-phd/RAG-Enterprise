"""Optimistic concurrency mixin."""

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column


class VersionMixin:
    """Row version used for optimistic concurrency control."""

    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
