"""Dense vector retrieval service."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.application.interfaces.embedding import EmbeddingProvider
from rag_enterprise.indexing.constants import DEFAULT_EMBEDDING_MODEL_ID
from rag_enterprise.indexing.repositories import EmbeddingRepository
from rag_enterprise.knowledge.enums import KnowledgeBaseStatus
from rag_enterprise.knowledge.repositories.knowledge_base import KnowledgeBaseRepository
from rag_enterprise.knowledge.repositories.scope import TenantScope
from rag_enterprise.processing.normalization import normalize_persian_text
from rag_enterprise.retrieval.exceptions import (
    ForbiddenRetrievalError,
    InvalidQueryError,
    KnowledgeBaseNotFoundError,
    KnowledgeBaseUnavailableError,
    ModelMismatchError,
    RetrievalError,
)
from rag_enterprise.retrieval.filters import build_filters
from rag_enterprise.retrieval.models import RetrievedChunk, SearchRequest, SearchResponse
from rag_enterprise.retrieval.ranking import candidate_pool_size, rank_dense_hits

logger = logging.getLogger(__name__)

MAX_TOP_K = 50


class RetrievalService:
    """Retrieve top-K chunks via dense cosine similarity over pgvector."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        embedding_provider: EmbeddingProvider,
        default_embedding_model_id: uuid.UUID = DEFAULT_EMBEDDING_MODEL_ID,
        embed_timeout_seconds: float = 30.0,
        search_timeout_seconds: float = 10.0,
    ) -> None:
        self._session_factory = session_factory
        self._provider = embedding_provider
        self._default_embedding_model_id = default_embedding_model_id
        self._embed_timeout_seconds = embed_timeout_seconds
        self._search_timeout_seconds = search_timeout_seconds

    async def retrieve(self, request: SearchRequest) -> SearchResponse:
        """Run authorization → normalize → embed → cosine pool → FAQ ranking → top-K."""
        started = time.perf_counter()
        # Same canonical pipeline as document processing (Feature 002 / RC2.1).
        query_text = normalize_persian_text(request.query_text).strip()
        if not query_text:
            raise InvalidQueryError()

        top_k = max(1, min(request.top_k, MAX_TOP_K))
        pool_k = candidate_pool_size(top_k, max_top_k=MAX_TOP_K)
        embedding_model_id = request.embedding_model_id or self._default_embedding_model_id

        if embedding_model_id != self._default_embedding_model_id:
            raise ModelMismatchError()

        if "knowledge_base:read" not in request.permissions:
            raise ForbiddenRetrievalError()

        async with self._session_factory() as session:
            kb_repo = KnowledgeBaseRepository(session)
            scope = TenantScope(
                organization_id=request.organization_id,
                workspace_id=request.workspace_id,
            )
            knowledge_base = await kb_repo.get_scoped(scope, request.knowledge_base_id)
            if knowledge_base is None:
                raise KnowledgeBaseNotFoundError()
            if knowledge_base.status != KnowledgeBaseStatus.ACTIVE:
                raise KnowledgeBaseUnavailableError()

            logger.info(
                "retrieval_started",
                extra={
                    "organization_id": str(request.organization_id),
                    "knowledge_base_id": str(request.knowledge_base_id),
                    "top_k": top_k,
                    "candidate_pool": pool_k,
                    "embedding_model_id": str(embedding_model_id),
                },
            )

            try:
                query_vector = await asyncio.wait_for(
                    self._provider.embed_query(query_text),
                    timeout=self._embed_timeout_seconds,
                )
            except TimeoutError as exc:
                raise RetrievalError("embedding_timeout", "Query embedding timed out") from exc
            except Exception as exc:
                raise RetrievalError("model_unavailable", str(exc)) from exc

            filters = build_filters(
                organization_id=request.organization_id,
                knowledge_base_id=request.knowledge_base_id,
                embedding_model_id=embedding_model_id,
                document_ids=request.document_ids,
                language=request.language,
            )
            embeddings_repo = EmbeddingRepository(session)
            indexed_count = await embeddings_repo.count_indexed_for_kb(
                organization_id=filters.organization_id,
                knowledge_base_id=filters.knowledge_base_id,
                embedding_model_id=filters.embedding_model_id,
            )

            warnings: list[str] = []
            if indexed_count == 0:
                warnings.append("no_indexed_content")
                response = SearchResponse(
                    query_text=query_text,
                    knowledge_base_id=request.knowledge_base_id,
                    embedding_model_id=embedding_model_id,
                    top_k=top_k,
                    results=[],
                    result_count=0,
                    warnings=warnings,
                )
                self._log_completed(started, 0, warnings)
                return response

            try:
                hits = await asyncio.wait_for(
                    embeddings_repo.search_cosine(
                        organization_id=filters.organization_id,
                        knowledge_base_id=filters.knowledge_base_id,
                        embedding_model_id=filters.embedding_model_id,
                        query_vector=query_vector,
                        top_k=pool_k,
                        document_ids=(list(filters.document_ids) if filters.document_ids else None),
                        language=filters.language,
                    ),
                    timeout=self._search_timeout_seconds,
                )
            except TimeoutError as exc:
                raise RetrievalError("search_timeout", "Vector search timed out") from exc

            if "document:read" not in request.permissions:
                hits = []

            cosine_results = [
                RetrievedChunk(
                    chunk_id=hit.chunk_id,
                    document_id=hit.document_id,
                    document_version_id=hit.document_version_id,
                    knowledge_base_id=hit.knowledge_base_id,
                    score=hit.score,
                    text=hit.text,
                    chunk_index=hit.chunk_index,
                    start_char=hit.start_char,
                    end_char=hit.end_char,
                    heading=hit.heading,
                    language=hit.language,
                )
                for hit in hits
            ]
            results, ranking_diagnostics = rank_dense_hits(
                query=query_text,
                chunks=cosine_results,
                top_k=top_k,
            )
            if not results and "no_indexed_content" not in warnings:
                warnings.append("no_results")

            response = SearchResponse(
                query_text=query_text,
                knowledge_base_id=request.knowledge_base_id,
                embedding_model_id=embedding_model_id,
                top_k=top_k,
                results=results,
                result_count=len(results),
                warnings=warnings,
            )
            self._log_completed(
                started,
                response.result_count,
                warnings,
                ranking_diagnostics=ranking_diagnostics.to_dict(),
            )
            return response

    @staticmethod
    def _log_completed(
        started: float,
        result_count: int,
        warnings: list[str],
        *,
        ranking_diagnostics: dict[str, object] | None = None,
    ) -> None:
        latency_ms = int((time.perf_counter() - started) * 1000)
        extra: dict[str, object] = {
            "result_count": result_count,
            "latency_ms": latency_ms,
            "warnings": warnings,
        }
        if ranking_diagnostics is not None:
            rankings = ranking_diagnostics.get("rankings")
            if isinstance(rankings, list) and rankings:
                top = rankings[0]
                if isinstance(top, dict):
                    extra["rank1_cosine"] = top.get("cosine_score")
                    extra["rank1_adjusted"] = top.get("adjusted_score")
                    extra["rank1_reasons"] = top.get("reasons_won")
        logger.info("retrieval_completed", extra=extra)
