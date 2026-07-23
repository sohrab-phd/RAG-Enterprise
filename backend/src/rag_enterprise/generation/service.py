"""RAG generation service."""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.application.interfaces.llm import LLMProvider
from rag_enterprise.generation.citations import (
    extract_markers,
    is_model_abstention,
    is_substantive_answer,
    salvage_top_chunk_citation,
    strip_question_echo,
    validate_citations,
)
from rag_enterprise.generation.evidence_selection import (
    EvidenceLabel,
    EvidenceSelectionResult,
    EvidenceSignals,
    ScoredEvidence,
    select_evidence,
)
from rag_enterprise.generation.exceptions import (
    GenerationError,
    GenerationTimeoutError,
    InvalidQuestionError,
    ModelUnavailableError,
    PromptTooLargeError,
)
from rag_enterprise.generation.models import (
    BuiltPrompt,
    GenerationRequest,
    GenerationResult,
    GenerationStatus,
    MessageRole,
    MessageTurn,
)
from rag_enterprise.generation.persistence import Conversation, Message
from rag_enterprise.generation.prompt_builder import PromptBuilder, PromptBuilderConfig
from rag_enterprise.generation.repositories import ConversationRepository, MessageRepository
from rag_enterprise.generation.templates import v1
from rag_enterprise.knowledge.repositories.scope import TenantScope
from rag_enterprise.retrieval.exceptions import KnowledgeBaseNotFoundError, RetrievalError
from rag_enterprise.retrieval.models import SearchRequest
from rag_enterprise.retrieval.service import RetrievalService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _CompletionRequest:
    system_prompt: str | None
    user_prompt: str


class GenerationService:
    """Orchestrate retrieve → sufficiency → prompt → LLM → citation validation."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        retrieval_service: RetrievalService,
        llm_provider: LLMProvider,
        prompt_builder: PromptBuilder | None = None,
        min_evidence_score: float = 0.25,
        max_history_messages: int = 6,
        default_top_k: int = 8,
        llm_timeout_seconds: float = 60.0,
        retry_delays_seconds: tuple[float, ...] = (0.0, 0.0),
    ) -> None:
        self._session_factory = session_factory
        self._retrieval = retrieval_service
        self._llm = llm_provider
        self._prompt_builder = prompt_builder or PromptBuilder(
            PromptBuilderConfig(max_history_messages=max_history_messages)
        )
        self._min_evidence_score = min_evidence_score
        self._max_history_messages = min(10, max(5, max_history_messages))
        self._default_top_k = default_top_k
        self._llm_timeout_seconds = llm_timeout_seconds
        self._retry_delays_seconds = retry_delays_seconds

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        started = time.perf_counter()
        question = request.question.strip()
        if not question:
            raise InvalidQuestionError()

        top_k = request.top_k or self._default_top_k
        conversation_id, history = await self._resolve_history(request)

        logger.info(
            "generation_started",
            extra={
                "organization_id": str(request.organization_id),
                "knowledge_base_id": str(request.knowledge_base_id),
                "top_k": top_k,
                "history_len": len(history),
            },
        )

        try:
            search = await self._retrieval.retrieve(
                SearchRequest(
                    query_text=question,
                    organization_id=request.organization_id,
                    workspace_id=request.workspace_id,
                    knowledge_base_id=request.knowledge_base_id,
                    top_k=top_k,
                    document_ids=request.document_ids,
                    user_id=request.user_id,
                    permissions=request.permissions,
                )
            )
        except KnowledgeBaseNotFoundError:
            raise
        except RetrievalError as exc:
            result = GenerationResult(
                status=GenerationStatus.FAILED,
                failure_reason="retrieval_failed",
                conversation_id=conversation_id,
                warnings=[exc.code],
            )
            conversation_id = await self._persist_turn(request, conversation_id, question, result)
            return result.model_copy(update={"conversation_id": conversation_id})

        chunk_ids = [chunk.chunk_id for chunk in search.results]
        max_score = max((chunk.score for chunk in search.results), default=0.0)
        response_language = self._prompt_builder.detect_language(question, request.language_hint)
        if search.result_count == 0 or max_score < self._min_evidence_score:
            result = GenerationResult(
                status=GenerationStatus.ABSTAINED,
                answer=v1.abstain_user_message(response_language),
                abstention_reason="insufficient_evidence",
                retrieved_chunks=list(search.results),
                retrieved_chunk_ids=chunk_ids,
                prompt_template_version=self._prompt_builder.template_version,
                conversation_id=conversation_id,
                warnings=list(search.warnings),
            )
            logger.info(
                "generation_abstained",
                extra={
                    "abstention_reason": "insufficient_evidence",
                    "result_count": search.result_count,
                },
            )
            conversation_id = await self._persist_turn(request, conversation_id, question, result)
            return result.model_copy(update={"conversation_id": conversation_id})

        # RC3.6: deterministic evidence selection after retrieval, before PromptBuilder.
        # Set RAG_EVIDENCE_SELECTION=0 only for local before/after benchmarks.
        if _evidence_selection_enabled():
            evidence = select_evidence(question=question, chunks=list(search.results))
        else:
            evidence = _passthrough_evidence(question=question, chunks=list(search.results))
        logger.info(
            "evidence_selected",
            extra={
                "selected_primary": evidence.selected_primary_ids,
                "selected_support": evidence.selected_support_ids,
                "discarded": evidence.discarded_ids,
                "conflict": evidence.conflict,
                "conflict_reason": evidence.conflict_reason,
                "selection_latency_ms": round(evidence.selection_latency_ms, 3),
                "candidate_count": len(search.results),
                "prompt_chunk_count": len(evidence.chunks_for_prompt),
            },
        )
        if not evidence.chunks_for_prompt:
            result = GenerationResult(
                status=GenerationStatus.ABSTAINED,
                answer=v1.abstain_user_message(response_language),
                abstention_reason="insufficient_evidence",
                retrieved_chunks=list(search.results),
                retrieved_chunk_ids=chunk_ids,
                prompt_template_version=self._prompt_builder.template_version,
                conversation_id=conversation_id,
                warnings=[*search.warnings, "evidence_selection_empty"],
            )
            logger.info(
                "generation_abstained",
                extra={"abstention_reason": "insufficient_evidence", "cause": "evidence_empty"},
            )
            conversation_id = await self._persist_turn(request, conversation_id, question, result)
            return result.model_copy(update={"conversation_id": conversation_id})

        try:
            built = self._prompt_builder.build(
                question=question,
                chunks=evidence.chunks_for_prompt,
                history=history,
                language_hint=request.language_hint,
            )
        except PromptTooLargeError as exc:
            result = GenerationResult(
                status=GenerationStatus.FAILED,
                failure_reason=exc.code,
                retrieved_chunks=list(search.results),
                retrieved_chunk_ids=chunk_ids,
                conversation_id=conversation_id,
            )
            conversation_id = await self._persist_turn(request, conversation_id, question, result)
            return result.model_copy(update={"conversation_id": conversation_id})

        try:
            content = await self._complete_with_retries(built)
        except GenerationTimeoutError as exc:
            result = GenerationResult(
                status=GenerationStatus.FAILED,
                failure_reason=exc.code,
                retrieved_chunks=built.chunks_used,
                retrieved_chunk_ids=[c.chunk_id for c in built.chunks_used],
                model_key=self._llm.model_key,
                prompt_template_version=built.template_version,
                conversation_id=conversation_id,
            )
            conversation_id = await self._persist_turn(request, conversation_id, question, result)
            return result.model_copy(update={"conversation_id": conversation_id})
        except (ModelUnavailableError, GenerationError) as exc:
            result = GenerationResult(
                status=GenerationStatus.FAILED,
                failure_reason=exc.code,
                retrieved_chunks=built.chunks_used,
                retrieved_chunk_ids=[c.chunk_id for c in built.chunks_used],
                model_key=self._llm.model_key,
                prompt_template_version=built.template_version,
                conversation_id=conversation_id,
            )
            conversation_id = await self._persist_turn(request, conversation_id, question, result)
            return result.model_copy(update={"conversation_id": conversation_id})

        abstain = is_model_abstention(content)
        if abstain is not None:
            result = GenerationResult(
                status=GenerationStatus.ABSTAINED,
                answer=v1.abstain_user_message(response_language),
                abstention_reason=abstain,
                retrieved_chunks=built.chunks_used,
                retrieved_chunk_ids=[c.chunk_id for c in built.chunks_used],
                model_key=self._llm.model_key,
                prompt_template_version=built.template_version,
                conversation_id=conversation_id,
            )
            conversation_id = await self._persist_turn(request, conversation_id, question, result)
            return result.model_copy(update={"conversation_id": conversation_id})

        cleaned = strip_question_echo(question, content)
        if not is_substantive_answer(cleaned):
            # Echo-only / empty after sanitization — never return the question as an answer.
            result = GenerationResult(
                status=GenerationStatus.ABSTAINED,
                answer=v1.abstain_user_message(response_language),
                abstention_reason="empty_or_echo_answer",
                retrieved_chunks=built.chunks_used,
                retrieved_chunk_ids=[c.chunk_id for c in built.chunks_used],
                model_key=self._llm.model_key,
                prompt_template_version=built.template_version,
                conversation_id=conversation_id,
            )
            conversation_id = await self._persist_turn(request, conversation_id, question, result)
            return result.model_copy(update={"conversation_id": conversation_id})

        citations = validate_citations(
            answer=cleaned,
            markers=built.markers,
            chunks=built.chunks_used,
        )
        if citations is None:
            # Evidence already passed the sufficiency gate and the model answered.
            # Salvage a top-chunk citation instead of a false abstain.
            citations = salvage_top_chunk_citation(
                chunks=built.chunks_used,
                markers=built.markers,
            )
        if citations is None:
            result = GenerationResult(
                status=GenerationStatus.ABSTAINED,
                answer=v1.abstain_user_message(response_language),
                abstention_reason="citation_validation_failed",
                retrieved_chunks=built.chunks_used,
                retrieved_chunk_ids=[c.chunk_id for c in built.chunks_used],
                model_key=self._llm.model_key,
                prompt_template_version=built.template_version,
                conversation_id=conversation_id,
            )
            conversation_id = await self._persist_turn(request, conversation_id, question, result)
            return result.model_copy(update={"conversation_id": conversation_id})

        # Ensure the user-facing answer still carries a citation marker when salvaged.
        final_answer = cleaned.strip()
        if not extract_markers(final_answer):
            final_answer = f"{final_answer} {citations[0].marker}".strip()

        result = GenerationResult(
            status=GenerationStatus.COMPLETED,
            answer=final_answer,
            citations=citations,
            retrieved_chunks=built.chunks_used,
            retrieved_chunk_ids=[c.chunk_id for c in built.chunks_used],
            model_key=self._llm.model_key,
            prompt_template_version=built.template_version,
            conversation_id=conversation_id,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "generation_completed",
            extra={
                "model_key": self._llm.model_key,
                "citation_count": len(citations),
                "latency_ms": latency_ms,
                "prompt_template_version": built.template_version,
            },
        )
        conversation_id = await self._persist_turn(request, conversation_id, question, result)
        return result.model_copy(update={"conversation_id": conversation_id})

    async def _complete_with_retries(self, built: BuiltPrompt) -> str:
        last_error: Exception | None = None
        attempts = max(1, len(self._retry_delays_seconds) + 1)
        completion_request = _CompletionRequest(
            system_prompt=built.system_prompt,
            user_prompt=built.user_prompt,
        )
        for attempt in range(attempts):
            try:
                response = await asyncio.wait_for(
                    self._llm.complete(completion_request),
                    timeout=self._llm_timeout_seconds,
                )
                return response.content
            except TimeoutError as exc:
                last_error = GenerationTimeoutError()
                last_error.__cause__ = exc
            except GenerationTimeoutError as exc:
                last_error = exc
            except Exception as exc:
                last_error = ModelUnavailableError(str(exc))
                last_error.__cause__ = exc
            if attempt < attempts - 1:
                delay = self._retry_delays_seconds[attempt]
                if delay > 0:
                    await asyncio.sleep(delay)
        assert last_error is not None
        raise last_error

    async def _resolve_history(
        self,
        request: GenerationRequest,
    ) -> tuple[uuid.UUID | None, list[MessageTurn]]:
        if request.history is not None:
            return request.conversation_id, self._prompt_builder.clamp_history(
                list(request.history)
            )
        if request.conversation_id is None:
            return None, []

        async with self._session_factory() as session:
            conversations = ConversationRepository(session)
            messages = MessageRepository(session)
            scope = TenantScope(
                organization_id=request.organization_id,
                workspace_id=request.workspace_id,
            )
            conversation = await conversations.get_scoped(scope, request.conversation_id)
            if conversation is None:
                return request.conversation_id, []
            turns = await messages.list_recent_turns(
                request.conversation_id,
                limit=self._max_history_messages,
            )
            return request.conversation_id, turns

    async def _persist_turn(
        self,
        request: GenerationRequest,
        conversation_id: uuid.UUID | None,
        question: str,
        result: GenerationResult,
    ) -> uuid.UUID:
        async with self._session_factory() as session:
            conversations = ConversationRepository(session)
            messages = MessageRepository(session)
            scope = TenantScope(
                organization_id=request.organization_id,
                workspace_id=request.workspace_id,
            )

            conversation: Conversation | None = None
            if conversation_id is not None:
                conversation = await conversations.get_scoped(scope, conversation_id)

            if conversation is None:
                conversation = Conversation(
                    organization_id=request.organization_id,
                    workspace_id=request.workspace_id,
                    user_id=request.user_id,
                    knowledge_base_id=request.knowledge_base_id,
                    status="active",
                    locale=request.language_hint,
                )
                await conversations.add(conversation)
                await session.flush()

            seq = await messages.next_sequence(conversation.id)
            await messages.add(
                Message(
                    organization_id=request.organization_id,
                    workspace_id=request.workspace_id,
                    conversation_id=conversation.id,
                    knowledge_base_id=request.knowledge_base_id,
                    role=MessageRole.USER,
                    content=question,
                    sequence_number=seq,
                )
            )
            assistant_content = result.answer or ""
            await messages.add(
                Message(
                    organization_id=request.organization_id,
                    workspace_id=request.workspace_id,
                    conversation_id=conversation.id,
                    knowledge_base_id=request.knowledge_base_id,
                    role=MessageRole.ASSISTANT,
                    content=assistant_content,
                    generation_status=result.status.value,
                    abstention_reason=result.abstention_reason or result.failure_reason,
                    model_key=result.model_key,
                    prompt_template_version=result.prompt_template_version,
                    sequence_number=seq + 1,
                )
            )
            await session.commit()
            return conversation.id


def _evidence_selection_enabled() -> bool:
    """Benchmark escape hatch — default on. Not part of the public API."""
    return os.environ.get("RAG_EVIDENCE_SELECTION", "1").strip().lower() not in {
        "0",
        "false",
        "off",
        "no",
    }


def _passthrough_evidence(
    *,
    question: str,
    chunks: list[object],
) -> EvidenceSelectionResult:
    """RC3.5-compatible path: send all retrieved chunks to PromptBuilder."""
    from rag_enterprise.retrieval.models import RetrievedChunk

    typed = [chunk for chunk in chunks if isinstance(chunk, RetrievedChunk)]
    scored = tuple(
        ScoredEvidence(
            chunk=chunk,
            label=EvidenceLabel.PRIMARY,
            selection_score=float(chunk.score),
            selection_reason="passthrough_disabled",
            signals=EvidenceSignals(
                lexical_overlap=0.0,
                persian_keyword_overlap=0.0,
                heading_similarity=0.0,
                faq_question_similarity=0.0,
                exact_phrase=0.0,
                numeric_agreement=0.0,
                named_entities=0.0,
                section_proximity=0.0,
                rc32_ranking_score=float(chunk.score),
                hybrid_rank_score=1.0 / (1.0 + index),
            ),
            retrieval_rank=index + 1,
        )
        for index, chunk in enumerate(typed)
    )
    return EvidenceSelectionResult(
        query=question,
        primary=tuple(typed),
        supplementary=(),
        discarded=(),
        scored=scored,
        conflict=False,
        conflict_reason=None,
        selection_latency_ms=0.0,
    )
