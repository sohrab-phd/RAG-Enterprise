"""Data transfer object base classes."""

from __future__ import annotations

from typing import Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")


class RequestDTO(BaseModel):
    """Base class for inbound application request payloads."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


class ResponseDTO(BaseModel):
    """Base class for outbound application response payloads."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class PaginationDTO[T](BaseModel):
    """Paginated response wrapper."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    items: list[T]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=500)
    total_items: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_items_length(self) -> Self:
        if len(self.items) > self.page_size:
            raise ValueError("items length cannot exceed page_size")
        return self

    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 0
        return (self.total_items + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages
