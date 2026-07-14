"""Chat / RAG generation HTTP routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from rag_enterprise.api.common.errors import ApplicationException
from rag_enterprise.api.common.responses import SuccessEnvelope, success_response
from rag_enterprise.application.common import ApplicationError, ErrorCode
from rag_enterprise.generation.api.dependencies import GenerationServiceDep
from rag_enterprise.generation.api.schemas import ChatRequest, ChatResponseDTO, CitationDTO
from rag_enterprise.generation.exceptions import GenerationError, InvalidQuestionError
from rag_enterprise.generation.models import GenerationRequest, GenerationStatus
from rag_enterprise.knowledge.api.dependencies import ActorDep
from rag_enterprise.retrieval.api.schemas import RetrievedChunkDTO

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["chat"])


@router.post(
    "/chat",
    response_model=SuccessEnvelope[ChatResponseDTO],
    status_code=status.HTTP_200_OK,
)
async def chat(
    workspace_id: uuid.UUID,
    body: ChatRequest,
    actor: ActorDep,
    service: GenerationServiceDep,
) -> SuccessEnvelope[ChatResponseDTO]:
    """Grounded RAG chat turn: retrieve → generate → cite or abstain."""
    try:
        result = await service.generate(
            GenerationRequest(
                question=body.question,
                organization_id=actor.organization_id,
                workspace_id=workspace_id,
                knowledge_base_id=body.knowledge_base_id,
                user_id=actor.user_id,
                permissions=frozenset(actor.permissions),
                conversation_id=body.conversation_id,
                document_ids=body.document_ids,
                language_hint=body.language_hint,
                top_k=body.top_k,
            )
        )
    except InvalidQuestionError as exc:
        raise ApplicationException(
            ApplicationError(
                code=ErrorCode.VALIDATION_FAILED,
                message=str(exc),
                details={"failure_reason": exc.code},
            )
        ) from exc
    except GenerationError as exc:
        raise ApplicationException(
            ApplicationError(
                code=ErrorCode.INTERNAL_ERROR,
                message=str(exc),
                details={"failure_reason": exc.code},
            )
        ) from exc

    return success_response(
        ChatResponseDTO(
            conversation_id=result.conversation_id,
            answer=result.answer,
            citations=[
                CitationDTO(
                    chunk_id=item.chunk_id,
                    document_id=item.document_id,
                    document_version_id=item.document_version_id,
                    rank=item.rank,
                    relevance_score=item.relevance_score,
                    excerpt=item.excerpt,
                    start_char=item.start_char,
                    end_char=item.end_char,
                    marker=item.marker,
                )
                for item in result.citations
            ],
            retrieved_chunks=[
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
                for item in result.retrieved_chunks
            ],
            abstained=result.status == GenerationStatus.ABSTAINED,
            status=result.status.value,
            abstention_reason=result.abstention_reason,
            failure_reason=result.failure_reason,
            model_key=result.model_key,
            prompt_template_version=result.prompt_template_version,
            warnings=list(result.warnings),
        )
    )
