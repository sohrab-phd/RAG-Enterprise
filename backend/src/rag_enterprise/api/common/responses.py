"""Standard API success response envelopes."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SuccessEnvelope[T](BaseModel):
    """Standard success response wrapper."""

    model_config = ConfigDict(frozen=True)

    success: Literal[True] = True
    data: T


class MetaEnvelope[T](BaseModel):
    """Success response wrapper with optional metadata."""

    model_config = ConfigDict(frozen=True)

    success: Literal[True] = True
    data: T
    meta: dict[str, Any] = Field(default_factory=dict)


def success_response[T](data: T) -> SuccessEnvelope[T]:
    """Build a standard success envelope."""
    return SuccessEnvelope(data=data)
