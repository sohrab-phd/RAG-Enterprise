# Embeddings & Retrieval

> **Status:** Implemented  
> **Specs:** [004 Embeddings](../../specs/004-embeddings/SPEC.md),
> [005 Retrieval](../../specs/005-retrieval/SPEC.md)

## Purpose

Convert persisted chunks into dense vectors (BGE-M3 by default), store them in
PostgreSQL with pgvector, and retrieve the most relevant chunks for a user query.

## Packages

```text
backend/src/rag_enterprise/indexing/
  providers/bge_m3.py   # EmbeddingProvider adapter
  models.py             # Chunk + Embedding ORM, IndexingResult
  repositories/         # ChunkRepository, EmbeddingRepository
  service.py            # IndexDocumentVersion / Reindex / Resume

backend/src/rag_enterprise/retrieval/
  service.py            # RetrievalService.retrieve()
  filters.py            # Metadata filter builder
  api/routes.py         # POST /workspaces/{id}/retrieve
```

## Embedding provider

Implements `EmbeddingProvider`:

- `embed_texts(texts)` — batch document embeddings
- `embed_query(text)` — single query embedding

Default model: `BAAI/bge-m3` (1024 dimensions).

| `EMBEDDING_BACKEND` | Behavior |
| --- | --- |
| `sentence_transformers` (**default / production**) | `SentenceTransformerEmbeddingProvider` — RC2.3–RC2.5 benchmark parity (`BAAI/bge-m3`, 1024-d) |
| `deterministic` | Hash-derived L2-normalized vectors for **CI/unit tests only** (explicit; never selected silently) |
| `flag` | Lazy-loads `FlagEmbedding.BGEM3FlagModel` |

HTTP, indexing, retrieval, generation, and the Persian RAG benchmark all resolve embeddings
through `create_embedding_provider(settings)` — the same factory. There is no secondary
path that quietly switches to deterministic.

## Indexing

```python
from rag_enterprise.indexing import IndexingService

await indexing_service.index_document_version(version_id)
await indexing_service.reindex_document_version(version_id)
await indexing_service.resume_failed_indexing(version_id)
```

Behavior:

- Batches of 32 texts (configurable)
- Skips chunks whose `content_hash` already has an `indexed` embedding
- Retries failed batches with split-on-failure
- Marks prior document versions `superseded` and embeddings `stale`

Prerequisite: `DocumentVersion.processing_status = chunked` with `chunk` rows persisted.

Configuration for embedding backends and dimensions is validated at process
startup. See [CONFIGURATION.md](CONFIGURATION.md).

## Retrieval API

`POST /api/v1/workspaces/{workspace_id}/retrieve`

```json
{
  "query": "سیاست مرخصی",
  "knowledge_base_id": "…",
  "document_ids": ["…"],
  "top_k": 8,
  "language": "fa"
}
```

Response uses `SuccessEnvelope` with ranked `RetrievedChunk` objects (`score` =
cosine similarity in `[0, 1]`).

Pipeline: authorize → embed query → metadata filters → cosine top-K → return chunks.

v1 supports **dense vector search only** (no BM25, hybrid, or reranking).

## Persistence

Migration `002_embeddings_indexing`:

- `chunk` table (version-scoped sequence, offsets, content_hash)
- `embedding` table (vector, dimensions, model, generation, index_status)
- PostgreSQL: `CREATE EXTENSION vector`, `vector(1024)`, HNSW cosine index

SQLite tests store vectors as JSON and compute cosine in Python.

## PostgreSQL integration tests

```bash
# With Postgres+pgvector running and a test database:
set RUN_POSTGRES_TESTS=1
set DATABASE_TEST_URL=postgresql+asyncpg://rag:rag_dev_password@localhost:5432/rag_enterprise_test
uv run pytest tests/indexing/test_postgres_integration.py
```

## Dev auth headers

Same as Knowledge Management:

- `X-User-Id`
- `X-Organization-Id`
