"""API pagination response models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from rag_enterprise.application.dto.base import PaginationDTO


class PaginationMeta(BaseModel):
    """Pagination metadata exposed through the API."""

    model_config = ConfigDict(frozen=True)

    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=500)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_next: bool
    has_previous: bool


class PaginatedData[T](BaseModel):
    """Paginated collection payload."""

    model_config = ConfigDict(frozen=True)

    items: list[T]
    pagination: PaginationMeta


class PaginatedEnvelope[T](BaseModel):
    """Standard success envelope for paginated collections."""

    model_config = ConfigDict(frozen=True)

    success: Literal[True] = True
    data: PaginatedData[T]


def paginated_response[T](page: PaginationDTO[T]) -> PaginatedEnvelope[T]:
    """Build a paginated success envelope from an application pagination DTO."""
    pagination = PaginationMeta(
        page=page.page,
        page_size=page.page_size,
        total_items=page.total_items,
        total_pages=page.total_pages,
        has_next=page.has_next,
        has_previous=page.page > 1,
    )
    return PaginatedEnvelope(data=PaginatedData(items=page.items, pagination=pagination))
