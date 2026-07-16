"""Result type for explicit success and failure handling."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from rag_enterprise.application.common.errors import ApplicationError

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Result[T]:
    """Represents the outcome of an application operation."""

    value: T | None
    error: ApplicationError | None

    def __post_init__(self) -> None:
        if self.is_success and self.error is not None:
            raise ValueError("Successful results must not contain an error")
        if self.is_failure and self.error is None:
            raise ValueError("Failed results must contain an error")

    @property
    def is_success(self) -> bool:
        return self.error is None

    @property
    def is_failure(self) -> bool:
        return self.error is not None

    @classmethod
    def ok(cls, value: T) -> Result[T]:
        return cls(value=value, error=None)

    @classmethod
    def fail(cls, error: ApplicationError) -> Result[T]:
        return cls(value=None, error=error)

    def unwrap(self) -> T:
        if self.is_failure:
            raise ValueError("Cannot unwrap a failed result")
        return self.value  # type: ignore[return-value]

    def map(self, func: Callable[[T], T]) -> Result[T]:
        if self.is_failure:
            if self.error is None:
                raise ValueError("Failed results must contain an error")
            return Result.fail(self.error)
        assert self.value is not None
        return Result.ok(func(self.value))
