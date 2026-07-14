# Process and Index (RC1.6)

> **Status:** Implemented  
> **Scope:** One synchronous operator action — no queues, workers, websockets, or SSE.

## Purpose

Expose the existing processing → chunking → embedding path through a single HTTP
action so operators can move a document from `uploaded` to `indexed` without a
background job system.

## Flow

```text
uploaded → extracting (processing) → extracted
       → chunking → chunked
       → indexing (embedding) → indexed
```

On failure the version is marked `failed` with `failure_reason` preserved.
Partial chunk/embedding rows from a failed re-run are cleared before re-chunking.

## Services

| Service | Role |
| --- | --- |
| `DocumentProcessingService` | Extract + normalize text |
| `ChunkingService` | Paragraph-aware chunks |
| `IndexingService` | Embed + persist vectors |
| `ProcessAndIndexService` | Synchronous orchestration |

## API

```http
POST /api/v1/workspaces/{workspace_id}/documents/{document_id}/process
```

Success envelope:

```json
{
  "success": true,
  "data": {
    "current_status": "indexed",
    "processed_chunks": 2,
    "indexed_embeddings": 2,
    "warnings": [],
    "document_version_id": "…"
  }
}
```

## Frontend

Knowledge document inspector: **Process & Index** button with a five-step
progress list (Uploaded → Processing → Chunking → Embedding → Indexed).
Progress during the request is optimistic client-side only (no polling/SSE).

## Testing

```bash
cd backend
uv run pytest tests/pipeline/test_process_api.py tests/e2e/test_rag_happy_path.py -q
```

## Related documents

- [Local File Storage](LOCAL_FILE_STORAGE.md)
- [E2E Happy Path](E2E_HAPPY_PATH.md)
- [Knowledge Management](KNOWLEDGE_MANAGEMENT.md)
- [Documentation index](../README.md)
