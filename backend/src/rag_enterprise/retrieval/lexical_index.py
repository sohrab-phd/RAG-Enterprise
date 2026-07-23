"""Lexical corpus persistence for BM25 without database schema changes.

Chunk text already lives in the chunk table from indexing. This module:
1. Loads that corpus through EmbeddingRepository filters.
2. Tokenizes with the shared Persian normalization pipeline.
3. Optionally persists tokenized documents under FILE_STORAGE_ROOT/.lexical/
   so restarts avoid re-tokenizing large knowledge bases.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.indexing.repositories.embedding import EmbeddingRepository, LexicalCorpusRow
from rag_enterprise.retrieval.bm25 import BM25Index, LexicalDocument, tokenize_lexical

logger = logging.getLogger(__name__)

_PROCESS_CACHE: dict[str, tuple[float, BM25Index]] = {}
_CACHE_TTL_SECONDS = 300.0


@dataclass(frozen=True)
class LexicalIndexMeta:
    organization_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    embedding_model_id: uuid.UUID
    document_count: int


def lexical_storage_root(file_storage_root: str | Path) -> Path:
    return Path(file_storage_root) / ".lexical"


def lexical_index_path(
    file_storage_root: str | Path,
    *,
    knowledge_base_id: uuid.UUID,
    embedding_model_id: uuid.UUID,
) -> Path:
    name = f"{knowledge_base_id}_{embedding_model_id}.json"
    return lexical_storage_root(file_storage_root) / name


def build_bm25_index(rows: list[LexicalCorpusRow]) -> BM25Index:
    documents = [
        LexicalDocument(
            chunk_id=str(row.chunk_id),
            document_id=str(row.document_id),
            document_version_id=str(row.document_version_id),
            knowledge_base_id=str(row.knowledge_base_id),
            chunk_index=row.chunk_index,
            start_char=row.start_char,
            end_char=row.end_char,
            heading=row.heading,
            language=row.language,
            text=row.text,
            tokens=tuple(tokenize_lexical(_index_text(row))),
        )
        for row in rows
    ]
    return BM25Index(documents)


def _index_text(row: LexicalCorpusRow) -> str:
    heading = (row.heading or "").strip()
    if heading:
        return f"{heading}\n{row.text}"
    return row.text


def _cache_key(
    *,
    organization_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    embedding_model_id: uuid.UUID,
    document_count: int,
) -> str:
    return f"{organization_id}:{knowledge_base_id}:{embedding_model_id}:{document_count}"


async def load_bm25_index(
    *,
    session: AsyncSession,
    organization_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    embedding_model_id: uuid.UUID,
    document_ids: list[uuid.UUID] | None,
    language: str | None,
    file_storage_root: str | Path | None = None,
) -> BM25Index:
    """Load BM25 index from process cache, side file, or live chunk corpus."""
    repo = EmbeddingRepository(session)
    rows = await repo.list_indexed_corpus(
        organization_id=organization_id,
        knowledge_base_id=knowledge_base_id,
        embedding_model_id=embedding_model_id,
        document_ids=document_ids,
        language=language,
    )
    cache_key = _cache_key(
        organization_id=organization_id,
        knowledge_base_id=knowledge_base_id,
        embedding_model_id=embedding_model_id,
        document_count=len(rows),
    )
    cached = _PROCESS_CACHE.get(cache_key)
    now = time.monotonic()
    if cached is not None and now - cached[0] <= _CACHE_TTL_SECONDS:
        return cached[1]

    index: BM25Index | None = None
    if file_storage_root is not None and not document_ids and language is None:
        path = lexical_index_path(
            file_storage_root,
            knowledge_base_id=knowledge_base_id,
            embedding_model_id=embedding_model_id,
        )
        index = _load_side_file(path, expected_count=len(rows))

    if index is None:
        index = build_bm25_index(rows)
        if file_storage_root is not None and not document_ids and language is None:
            _write_side_file(
                lexical_index_path(
                    file_storage_root,
                    knowledge_base_id=knowledge_base_id,
                    embedding_model_id=embedding_model_id,
                ),
                rows=rows,
            )

    _PROCESS_CACHE[cache_key] = (now, index)
    return index


async def persist_kb_lexical_index(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    organization_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    embedding_model_id: uuid.UUID,
    file_storage_root: str | Path,
) -> LexicalIndexMeta:
    """Rebuild the on-disk lexical token index after embedding indexing."""
    async with session_factory() as session:
        repo = EmbeddingRepository(session)
        rows = await repo.list_indexed_corpus(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            embedding_model_id=embedding_model_id,
            document_ids=None,
            language=None,
        )
    path = lexical_index_path(
        file_storage_root,
        knowledge_base_id=knowledge_base_id,
        embedding_model_id=embedding_model_id,
    )
    _write_side_file(path, rows=rows)
    # Drop stale process caches for this KB.
    prefix = f"{organization_id}:{knowledge_base_id}:{embedding_model_id}:"
    for key in list(_PROCESS_CACHE):
        if key.startswith(prefix):
            del _PROCESS_CACHE[key]
    logger.info(
        "lexical_index_persisted",
        extra={
            "knowledge_base_id": str(knowledge_base_id),
            "document_count": len(rows),
            "path": str(path),
        },
    )
    return LexicalIndexMeta(
        organization_id=organization_id,
        knowledge_base_id=knowledge_base_id,
        embedding_model_id=embedding_model_id,
        document_count=len(rows),
    )


def clear_lexical_process_cache() -> None:
    """Test helper to drop process-level BM25 caches."""
    _PROCESS_CACHE.clear()


def _write_side_file(path: Path, *, rows: list[LexicalCorpusRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "document_count": len(rows),
        "documents": [
            {
                "chunk_id": str(row.chunk_id),
                "document_id": str(row.document_id),
                "document_version_id": str(row.document_version_id),
                "knowledge_base_id": str(row.knowledge_base_id),
                "chunk_index": row.chunk_index,
                "start_char": row.start_char,
                "end_char": row.end_char,
                "heading": row.heading,
                "language": row.language,
                "text": row.text,
                "tokens": tokenize_lexical(_index_text(row)),
            }
            for row in rows
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _load_side_file(path: Path, *, expected_count: int) -> BM25Index | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if int(payload.get("document_count") or -1) != expected_count:
        return None
    documents_raw = payload.get("documents")
    if not isinstance(documents_raw, list):
        return None
    documents: list[LexicalDocument] = []
    for item in documents_raw:
        if not isinstance(item, dict):
            continue
        tokens_raw = item.get("tokens")
        tokens = tuple(str(token) for token in tokens_raw) if isinstance(tokens_raw, list) else ()
        if not tokens:
            tokens = tuple(tokenize_lexical(str(item.get("text") or "")))
        documents.append(
            LexicalDocument(
                chunk_id=str(item["chunk_id"]),
                document_id=str(item["document_id"]),
                document_version_id=str(item["document_version_id"]),
                knowledge_base_id=str(item["knowledge_base_id"]),
                chunk_index=int(item.get("chunk_index") or 0),
                start_char=int(item.get("start_char") or 0),
                end_char=int(item.get("end_char") or 0),
                heading=item.get("heading"),
                language=item.get("language"),
                text=str(item.get("text") or ""),
                tokens=tokens,
            )
        )
    if len(documents) != expected_count:
        return None
    return BM25Index(documents)
