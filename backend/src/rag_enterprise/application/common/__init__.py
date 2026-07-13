"""Shared application primitives."""

from rag_enterprise.application.common.errors import ApplicationError, ErrorCode
from rag_enterprise.application.common.result import Result

__all__ = ["ApplicationError", "ErrorCode", "Result"]
