"""Retrieval HTTP routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from rag_enterprise.api.common.errors import ApplicationException
from rag_enterprise.api.common.responses import SuccessEnvelope, success_response
from rag_enterprise.application.common import ApplicationError, ErrorCode
from rag_enterprise.knowledge.api.dependencies import ActorDep
from rag_enterprise.retrieval.api.dependencies import RetrievalServiceDep
from rag_enterprise.retrieval.api.schemas import (
    RetrievedChunkDTO,
    RetrieveRequest,
    RetrieveResponseDTO,
)
from rag_enterprise.retrieval.exceptions import RetrievalError
from rag_enterprise.retrieval.models import SearchRequest

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["retrieval"])


@router.post(
    "/retrieve",
    response_model=SuccessEnvelope[RetrieveResponseDTO],
    status_code=status.HTTP_200_OK,
)
async def retrieve(
    workspace_id: uuid.UUID,
    body: RetrieveRequest,
    actor: ActorDep,
    service: RetrievalServiceDep,
) -> SuccessEnvelope[RetrieveResponseDTO]:
    """Dense vector retrieval over an authorized knowledge base."""
    try:
        response = await service.retrieve(
            SearchRequest(
                query_text=body.query,
                organization_id=actor.organization_id,
                workspace_id=workspace_id,
                knowledge_base_id=body.knowledge_base_id,
                top_k=body.top_k,
                document_ids=body.document_ids,
                language=body.language,
                user_id=actor.user_id,
                permissions=frozenset(actor.permissions),
            )
        )
    except RetrievalError as exc:
        raise ApplicationException(_map_retrieval_error(exc)) from exc

    return success_response(
        RetrieveResponseDTO(
            query=response.query_text,
            knowledge_base_id=response.knowledge_base_id,
            embedding_model_id=response.embedding_model_id,
            top_k=response.top_k,
            results=[
                RetrievedChunkDTO(
                    chunk_id=item.chunk_id,
                    document_id=item.document_id,
                    document_version_id=item.document_version_id,
                    knowledge_base_id=item.knowledge_base_id,
                    score=item.score,
                    text=item.text,
                    chunk_index=item.chunk_index,
                    start_char=item.start_char,
                    end_char=item.end_char,
                    heading=item.heading,
                    language=item.language,
                )
                for item in response.results
            ],
            result_count=response.result_count,
            warnings=list(response.warnings),
        )
    )


def _map_retrieval_error(exc: RetrievalError) -> ApplicationError:
    mapping = {
        "invalid_query": ErrorCode.VALIDATION_FAILED,
        "forbidden": ErrorCode.FORBIDDEN,
        "knowledge_base_not_found": ErrorCode.NOT_FOUND,
        "knowledge_base_unavailable": ErrorCode.CONFLICT,
        "model_mismatch": ErrorCode.VALIDATION_FAILED,
        "model_unavailable": ErrorCode.INTERNAL_ERROR,
        "embedding_timeout": ErrorCode.INTERNAL_ERROR,
        "search_timeout": ErrorCode.INTERNAL_ERROR,
    }
    return ApplicationError(
        code=mapping.get(exc.code, ErrorCode.INTERNAL_ERROR),
        message=str(exc),
        details={"failure_reason": exc.code},
    )
