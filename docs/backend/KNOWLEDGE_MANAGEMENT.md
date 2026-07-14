# Knowledge Management Implementation

> **Status:** Implemented per `specs/001-knowledge-management/`  
> **Module:** `backend/src/rag_enterprise/knowledge/`

## Overview

Feature 001 delivers workspace-scoped knowledge base administration, folder hierarchy,
document lifecycle, upload sessions, and document versioning. Chunking, embeddings,
retrieval, and chat are intentionally excluded.

## Package layout

```text
knowledge/
  models.py              SQLAlchemy ORM models
  enums.py               Domain enumerations
  commands.py            Write-side commands
  queries.py             Read-side queries
  dto.py                 Request/response DTOs
  handlers/              Command and query handlers
  repositories/          Tenant-scoped repositories
  unit_of_work.py        KnowledgeUnitOfWork
  registration.py        Dispatcher registration
  api/routes.py          FastAPI endpoints
  infrastructure/        FileSystemStorage (runtime) + InMemoryFileStorage (tests)
```

Binary uploads use local disk via [Local File Storage (RC1.6)](LOCAL_FILE_STORAGE.md)
(`FILE_STORAGE_ROOT`, default `storage/uploads`). Tests keep `InMemoryFileStorage`.

After upload, operators run synchronous
[Process & Index](PROCESS_AND_INDEX.md)
(`POST .../documents/{document_id}/process`).

## Knowledge base lifecycle

```text
Draft → Publish → Active → Archive → Restore → Active
```

| Transition | Endpoint |
| --- | --- |
| Create (starts as `draft`) | `POST .../knowledge-bases` |
| Publish (`draft` → `active`) | `POST .../knowledge-bases/{id}/publish` |
| Archive | `POST .../knowledge-bases/{id}/archive` |
| Restore (`archived` → `active`) | `POST .../knowledge-bases/{id}/restore` |

Do **not** use archive → restore to activate a draft KB. Publishing does not change
retrieval rules: search still requires an `active` knowledge base.

## API surface

Base path: `/api/v1/workspaces/{workspace_id}/knowledge-bases/...`

Responses use the platform `SuccessEnvelope` and `PaginatedEnvelope` contracts.

### Development authentication

Until identity is implemented, pass actor headers:

| Header | Purpose |
| --- | --- |
| `X-User-Id` | Acting user UUID |
| `X-Organization-Id` | Tenant organization UUID |

All knowledge permissions are granted when both headers are present (development stub).

## Persistence

- ORM models: `KnowledgeBase`, `Folder`, `Document`, `DocumentVersion`, `UploadSession`
- Migration: `alembic/versions/001_initial_knowledge.py`
- UUIDv7 primary keys, soft delete on KB/folder/document, optimistic `row_version`

Run migrations:

```bash
cd backend
uv run alembic upgrade head
```

## Application flow

1. FastAPI route validates request DTO
2. Command/query dispatched through application layer
3. Handler uses `KnowledgeUnitOfWork` for transaction boundary
4. Handler returns `Result[T]`; routes map failures to `ApplicationException`

## Testing

Tests live in `backend/tests/knowledge/`:

- Repository tenant and soft-delete filtering
- Command handler unit tests
- API integration tests (SQLite in-memory)

## Related documents

- [specs/001-knowledge-management/README.md](../../specs/001-knowledge-management/README.md)
- [API Foundation](API_FOUNDATION.md)
- [Application Layer](APPLICATION_LAYER.md)
- [Persistence Layer](PERSISTENCE_LAYER.md)
