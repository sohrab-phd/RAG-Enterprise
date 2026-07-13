"""Knowledge API dependencies."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from rag_enterprise.api.common.errors import ApplicationException
from rag_enterprise.application.commands.dispatcher import CommandDispatcher
from rag_enterprise.application.common import ApplicationError, ErrorCode, Result
from rag_enterprise.application.queries.dispatcher import QueryDispatcher
from rag_enterprise.core.dependencies.providers import get_container
from rag_enterprise.knowledge.authorization import ALL_KNOWLEDGE_PERMISSIONS
from rag_enterprise.knowledge.context import RequestActor


def get_command_dispatcher() -> CommandDispatcher:
    return get_container().command_dispatcher


def get_query_dispatcher() -> QueryDispatcher:
    return get_container().query_dispatcher


def get_request_actor(
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    x_organization_id: Annotated[str | None, Header(alias="X-Organization-Id")] = None,
) -> RequestActor:
    """Resolve actor from development headers until authentication is implemented."""
    if x_user_id is None or x_organization_id is None:
        raise HTTPException(status_code=401, detail="Missing actor headers")
    return RequestActor(
        user_id=uuid.UUID(x_user_id),
        organization_id=uuid.UUID(x_organization_id),
        permissions=ALL_KNOWLEDGE_PERMISSIONS,
    )


CommandDispatcherDep = Annotated[CommandDispatcher, Depends(get_command_dispatcher)]
QueryDispatcherDep = Annotated[QueryDispatcher, Depends(get_query_dispatcher)]
ActorDep = Annotated[RequestActor, Depends(get_request_actor)]


def raise_for_result[T](result: Result[T]) -> T:
    if result.is_failure:
        if result.error is None:
            raise ApplicationException(
                ApplicationError(code=ErrorCode.INTERNAL_ERROR, message="Unknown error")
            )
        raise ApplicationException(result.error)
    return result.unwrap()
