"""Execute the real production retrieval + generation pipeline."""

from __future__ import annotations

import time

from rag_enterprise.core.dependencies.providers import AppContainer
from rag_enterprise.generation.models import GenerationRequest, GenerationStatus
from rag_enterprise.generation.prompt_builder import PromptBuilder
from rag_enterprise.processing.language import detect_language
from rag_enterprise.processing.normalization import normalize_persian_text
from rag_enterprise.retrieval.models import SearchRequest
from tools.persian_rag_benchmark.config import BenchmarkConfig
from tools.persian_rag_benchmark.models import (
    GroundTruthQuestion,
    QuestionRunResult,
    RetrievedEvidence,
)
from tools.persian_rag_benchmark.persian_text import diagnose_language_surface


async def run_pipeline_for_questions(
    container: AppContainer,
    questions: list[GroundTruthQuestion],
    *,
    config: BenchmarkConfig,
) -> list[QuestionRunResult]:
    """Call production RetrievalService (+ optional GenerationService) for each question."""
    assert container.retrieval_service is not None
    assert config.knowledge_base_id is not None

    results: list[QuestionRunResult] = []
    for question in questions:
        results.append(
            await _run_one(
                container,
                question,
                config=config,
            )
        )
    return results


async def _run_one(
    container: AppContainer,
    question: GroundTruthQuestion,
    *,
    config: BenchmarkConfig,
) -> QuestionRunResult:
    assert container.retrieval_service is not None
    kb_id = config.knowledge_base_id
    assert kb_id is not None

    normalized = normalize_persian_text(question.question)
    language_issues = diagnose_language_surface(question.question)
    detected = detect_language(question.question)

    started = time.perf_counter()
    retrieval = await container.retrieval_service.retrieve(
        SearchRequest(
            query_text=question.question,
            organization_id=config.organization_id,
            workspace_id=config.workspace_id,
            knowledge_base_id=kb_id,
            top_k=config.top_k,
            language="fa",
            user_id=config.user_id,
            permissions=config.permissions,
        )
    )
    retrieval_ms = int((time.perf_counter() - started) * 1000)

    evidence: list[RetrievedEvidence] = []
    for rank, chunk in enumerate(retrieval.results, start=1):
        evidence.append(
            RetrievedEvidence(
                chunk_id=str(chunk.chunk_id),
                document_id=str(chunk.document_id),
                document_version_id=str(chunk.document_version_id),
                score=float(chunk.score),
                rank=rank,
                text=chunk.text,
                language=chunk.language,
            )
        )

    retrieved_ids = [item.chunk_id for item in evidence]
    hit = question.expected_chunk_id in retrieved_ids
    rank = retrieved_ids.index(question.expected_chunk_id) + 1 if hit else None
    correct_document = any(item.document_id == question.expected_document_id for item in evidence)
    avg_score = sum(item.score for item in evidence) / len(evidence) if evidence else None

    generated_answer: str | None = None
    citations: list[str] = []
    generation_status: str | None = None
    abstained = False
    generation_ms: int | None = None
    prompt_preview: str | None = None
    gen_scores: dict[str, float | bool | None] = {}

    if config.include_generation and container.generation_service is not None:
        prompt_preview = (
            PromptBuilder()
            .build(
                question=question.question,
                chunks=list(retrieval.results),
                history=[],
                language_hint="fa",
            )
            .user_prompt[:500]
        )
        gen_started = time.perf_counter()
        generation = await container.generation_service.generate(
            GenerationRequest(
                question=question.question,
                organization_id=config.organization_id,
                workspace_id=config.workspace_id,
                knowledge_base_id=kb_id,
                user_id=config.user_id,
                permissions=config.permissions,
                history=[],
                language_hint="fa",
                top_k=config.top_k,
            )
        )
        generation_ms = int((time.perf_counter() - gen_started) * 1000)
        generated_answer = generation.answer
        citations = [str(item.chunk_id) for item in generation.citations]
        generation_status = str(generation.status)
        abstained = generation.status == GenerationStatus.ABSTAINED
        gen_scores = _score_generation(question, generation.answer, citations)

    e2e_ms = retrieval_ms + (generation_ms or 0)
    return QuestionRunResult(
        question_id=question.id,
        question=question.question,
        normalized_question=normalized,
        category=question.category.value,
        difficulty=question.difficulty.value,
        robustness_kind=question.robustness_kind.value,
        parent_question_id=question.parent_question_id,
        gold_answer=question.gold_answer,
        expected_chunk_id=question.expected_chunk_id,
        expected_document_id=question.expected_document_id,
        retrieved=evidence,
        retrieval_hit=hit,
        retrieval_rank=rank,
        correct_document=correct_document,
        correct_chunk=hit,
        avg_retrieval_score=avg_score,
        detected_language=detected,
        prompt_preview=prompt_preview,
        generated_answer=generated_answer,
        citations=citations,
        generation_status=generation_status,
        abstained=abstained,
        retrieval_latency_ms=retrieval_ms,
        generation_latency_ms=generation_ms,
        e2e_latency_ms=e2e_ms,
        language_issues=language_issues,
        generation_scores=gen_scores,
        warnings=list(retrieval.warnings) if hasattr(retrieval, "warnings") else [],
    )


def _score_generation(
    question: GroundTruthQuestion,
    answer: str | None,
    citations: list[str],
) -> dict[str, float | bool | None]:
    from tools.persian_rag_benchmark.diagnostics.generation import score_answer

    return score_answer(
        gold=question.gold_answer,
        predicted=answer,
        expected_chunk_id=question.expected_chunk_id,
        cited_chunk_ids=citations,
        expected_citation_text=question.expected_citation_text,
        category=question.category.value,
    )
