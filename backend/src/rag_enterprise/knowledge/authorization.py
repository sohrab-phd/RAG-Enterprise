"""Authorization helpers for knowledge operations."""

from __future__ import annotations

from rag_enterprise.application.common import ApplicationError, ErrorCode, Result
from rag_enterprise.knowledge.context import RequestActor

ALL_KNOWLEDGE_PERMISSIONS = frozenset(
    {
        "workspace:knowledge_base:create",
        "knowledge_base:read",
        "knowledge_base:manage",
        "folder:read",
        "folder:manage",
        "document:read",
        "document:create",
        "document:update",
        "document:delete",
        "document:download",
    }
)


def require_permission(actor: RequestActor, permission: str) -> Result[None]:
    if not actor.has_permission(permission):
        return Result.fail(ApplicationError(code=ErrorCode.FORBIDDEN, message="Permission denied"))
    return Result.ok(None)


def not_found(resource: str) -> Result[None]:
    return Result.fail(ApplicationError(code=ErrorCode.NOT_FOUND, message=f"{resource} not found"))


def conflict(message: str, **details: object) -> Result[None]:
    return Result.fail(
        ApplicationError(
            code=ErrorCode.CONFLICT,
            message=message,
            details={key: value for key, value in details.items()},
        )
    )
