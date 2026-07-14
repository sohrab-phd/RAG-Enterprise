"""Process-and-index HTTP routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from rag_enterprise.api.common.errors import ApplicationException
from rag_enterprise.api.common.responses import SuccessEnvelope, success_response
from rag_enterprise.application.common.errors import ApplicationError, ErrorCode
from rag_enterprise.core.dependencies.providers import get_container
from rag_enterprise.knowledge.api.dependencies import ActorDep
from rag_enterprise.pipeline.api.schemas import ProcessAndIndexResponseDTO
from rag_enterprise.pipeline.service import ProcessAndIndexError, ProcessAndIndexService

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["documents"])


def get_process_and_index_service() -> ProcessAndIndexService:
    container = get_container()
    if container.process_and_index_service is None:
        raise RuntimeError("ProcessAndIndexService is not initialized")
    return container.process_and_index_service


ProcessAndIndexDep = Annotated[ProcessAndIndexService, Depends(get_process_and_index_service)]


@router.post(
    "/documents/{document_id}/process",
    response_model=SuccessEnvelope[ProcessAndIndexResponseDTO],
    status_code=status.HTTP_200_OK,
    summary="Process and index document",
)
async def process_and_index_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    actor: ActorDep,
    service: ProcessAndIndexDep,
) -> SuccessEnvelope[ProcessAndIndexResponseDTO]:
    """Synchronously run processing → chunking → embedding → indexed."""
    if "document:update" not in actor.permissions and "document:create" not in actor.permissions:
        raise ApplicationException(
            ApplicationError(
                code=ErrorCode.FORBIDDEN, message="Missing document process permission"
            )
        )
    try:
        result = await service.process_document(
            organization_id=actor.organization_id,
            workspace_id=workspace_id,
            document_id=document_id,
        )
    except ProcessAndIndexError as exc:
        code = {
            "not_found": ErrorCode.NOT_FOUND,
            "conflict": ErrorCode.CONFLICT,
            "internal_error": ErrorCode.INTERNAL_ERROR,
        }.get(exc.code, ErrorCode.INTERNAL_ERROR)
        details = dict(exc.details)
        if exc.current_status is not None:
            details["current_status"] = exc.current_status
        raise ApplicationException(
            ApplicationError(code=code, message=exc.message, details=details)
        ) from exc

    return success_response(
        ProcessAndIndexResponseDTO(
            current_status=result.current_status,
            processed_chunks=result.processed_chunks,
            indexed_embeddings=result.indexed_embeddings,
            warnings=list(result.warnings),
            document_version_id=(
                str(result.document_version_id) if result.document_version_id else None
            ),
        )
    )
