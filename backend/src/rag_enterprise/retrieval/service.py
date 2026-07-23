"""Hybrid dense + BM25 retrieval service with RC3.2 final calibration."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.application.interfaces.embedding import EmbeddingProvider
from rag_enterprise.indexing.constants import DEFAULT_EMBEDDING_MODEL_ID
from rag_enterprise.indexing.repositories import EmbeddingRepository
from rag_enterprise.knowledge.enums import KnowledgeBaseStatus
from rag_enterprise.knowledge.repositories.knowledge_base import KnowledgeBaseRepository
from rag_enterprise.knowledge.repositories.scope import TenantScope
from rag_enterprise.processing.normalization import normalize_persian_text
from rag_enterprise.retrieval.bm25 import tokenize_lexical
from rag_enterprise.retrieval.exceptions import (
    ForbiddenRetrievalError,
    InvalidQueryError,
    KnowledgeBaseNotFoundError,
    KnowledgeBaseUnavailableError,
    ModelMismatchError,
    RetrievalError,
)
from rag_enterprise.retrieval.filters import build_filters
from rag_enterprise.retrieval.hybrid import (
    apply_persian_bm25_boosts,
    blend_cosine_with_rrf,
    fuse_dense_and_bm25,
    hybrid_pool_size,
    rc32_candidate_cap,
)
from rag_enterprise.retrieval.lexical_index import load_bm25_index
from rag_enterprise.retrieval.models import RetrievedChunk, SearchRequest, SearchResponse
from rag_enterprise.retrieval.ranking import rank_dense_hits

logger = logging.getLogger(__name__)

MAX_TOP_K = 50


class RetrievalService:
    """Retrieve top-K chunks via dense + BM25 hybrid search, then RC3.2 ranking."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        embedding_provider: EmbeddingProvider,
        default_embedding_model_id: uuid.UUID = DEFAULT_EMBEDDING_MODEL_ID,
        embed_timeout_seconds: float = 30.0,
        search_timeout_seconds: float = 10.0,
        file_storage_root: str | Path | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._provider = embedding_provider
        self._default_embedding_model_id = default_embedding_model_id
        self._embed_timeout_seconds = embed_timeout_seconds
        self._search_timeout_seconds = search_timeout_seconds
        self._file_storage_root = file_storage_root

    async def retrieve(self, request: SearchRequest) -> SearchResponse:
        """Normalize → embed → dense+BM25 → RRF → RC3.2 FAQ calibration → top-K."""
        started = time.perf_counter()
        # Same canonical pipeline as document processing (Feature 002 / RC2.1).
        query_text = normalize_persian_text(request.query_text).strip()
        if not query_text:
            raise InvalidQueryError()

        top_k = max(1, min(request.top_k, MAX_TOP_K))
        pool_k = hybrid_pool_size()
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
                    "retrieval_mode": "hybrid_dense_bm25_rrf",
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
                dense_hits = await asyncio.wait_for(
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
                bm25_index = await asyncio.wait_for(
                    load_bm25_index(
                        session=session,
                        organization_id=filters.organization_id,
                        knowledge_base_id=filters.knowledge_base_id,
                        embedding_model_id=filters.embedding_model_id,
                        document_ids=(list(filters.document_ids) if filters.document_ids else None),
                        language=filters.language,
                        file_storage_root=self._file_storage_root,
                    ),
                    timeout=self._search_timeout_seconds,
                )
            except TimeoutError as exc:
                raise RetrievalError("search_timeout", "Hybrid search timed out") from exc

            if "document:read" not in request.permissions:
                dense_hits = []

            dense_chunks = [
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
                for hit in dense_hits
            ]
            dense_by_id = {str(chunk.chunk_id): chunk for chunk in dense_chunks}
            dense_ids = [str(chunk.chunk_id) for chunk in dense_chunks]
            dense_scores = {str(chunk.chunk_id): float(chunk.score) for chunk in dense_chunks}

            query_tokens = tokenize_lexical(query_text)
            raw_bm25 = bm25_index.search(query_tokens, top_k=pool_k)
            bm25_hits = apply_persian_bm25_boosts(
                query=query_text,
                index=bm25_index,
                hits=raw_bm25,
            )
            if "document:read" not in request.permissions:
                bm25_hits = []
            bm25_ids = [hit.chunk_id for hit in bm25_hits]
            bm25_scores = {hit.chunk_id: float(hit.score) for hit in bm25_hits}

            fused_ids, rrf_scores, hybrid_diagnostics = fuse_dense_and_bm25(
                dense_ids=dense_ids,
                bm25_ids=bm25_ids,
                dense_scores=dense_scores,
                bm25_scores=bm25_scores,
                limit=max(top_k, rc32_candidate_cap()),
            )
            max_rrf = max(rrf_scores.values()) if rrf_scores else 0.0

            missing_ids = [
                uuid.UUID(chunk_id) for chunk_id in fused_ids if chunk_id not in dense_by_id
            ]
            cosine_backfill: dict[uuid.UUID, float] = {}
            if missing_ids:
                cosine_backfill = await embeddings_repo.cosine_for_chunk_ids(
                    organization_id=filters.organization_id,
                    knowledge_base_id=filters.knowledge_base_id,
                    embedding_model_id=filters.embedding_model_id,
                    query_vector=query_vector,
                    chunk_ids=missing_ids,
                )

            fused_chunks: list[RetrievedChunk] = []
            for chunk_id in fused_ids:
                existing = dense_by_id.get(chunk_id)
                if existing is not None:
                    blended = blend_cosine_with_rrf(
                        cosine_score=float(existing.score),
                        rrf_score=rrf_scores.get(chunk_id, 0.0),
                        max_rrf_score=max_rrf,
                    )
                    fused_chunks.append(existing.model_copy(update={"score": blended}))
                    continue
                lexical_doc = bm25_index.document(chunk_id)
                if lexical_doc is None:
                    continue
                chunk_uuid = uuid.UUID(chunk_id)
                cosine = float(cosine_backfill.get(chunk_uuid, 0.0))
                blended = blend_cosine_with_rrf(
                    cosine_score=cosine,
                    rrf_score=rrf_scores.get(chunk_id, 0.0),
                    max_rrf_score=max_rrf,
                )
                fused_chunks.append(
                    RetrievedChunk(
                        chunk_id=chunk_uuid,
                        document_id=uuid.UUID(lexical_doc.document_id),
                        document_version_id=uuid.UUID(lexical_doc.document_version_id),
                        knowledge_base_id=uuid.UUID(lexical_doc.knowledge_base_id),
                        score=blended,
                        text=lexical_doc.text,
                        chunk_index=lexical_doc.chunk_index,
                        start_char=lexical_doc.start_char,
                        end_char=lexical_doc.end_char,
                        heading=lexical_doc.heading,
                        language=lexical_doc.language,
                    )
                )

            results, ranking_diagnostics = rank_dense_hits(
                query=query_text,
                chunks=fused_chunks,
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
                hybrid_diagnostics=hybrid_diagnostics.to_dict(),
            )
            return response

    @staticmethod
    def _log_completed(
        started: float,
        result_count: int,
        warnings: list[str],
        *,
        ranking_diagnostics: dict[str, object] | None = None,
        hybrid_diagnostics: dict[str, object] | None = None,
    ) -> None:
        latency_ms = int((time.perf_counter() - started) * 1000)
        extra: dict[str, object] = {
            "result_count": result_count,
            "latency_ms": latency_ms,
            "warnings": warnings,
        }
        if hybrid_diagnostics is not None:
            extra["hybrid"] = hybrid_diagnostics
        if ranking_diagnostics is not None:
            rankings = ranking_diagnostics.get("rankings")
            if isinstance(rankings, list) and rankings:
                top = rankings[0]
                if isinstance(top, dict):
                    extra["rank1_cosine"] = top.get("cosine_score")
                    extra["rank1_adjusted"] = top.get("adjusted_score")
                    extra["rank1_reasons"] = top.get("reasons_won")
        logger.info("retrieval_completed", extra=extra)
