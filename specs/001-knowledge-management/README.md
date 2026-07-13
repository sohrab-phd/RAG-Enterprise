# Knowledge Management

> **Spec ID:** 001  
> **Status:** Draft — architecture and specification only  
> **Bounded context:** Knowledge Content  
> **Authority:** Implements approved domain and data architecture

## Purpose

Knowledge Management is the first business capability of RAG-enterprise. It lets workspace
members create curated knowledge corpora, organize documents hierarchically, upload and
version content, and govern lifecycle states from draft through archival.

The capability owns the **Knowledge Content** bounded context:

- `KnowledgeBase`
- `Folder`
- `Document`
- `DocumentVersion`

It coordinates with **Knowledge Indexing** through domain events when a version is ready
for extraction, chunking, and embedding. It does not own retrieval configuration,
conversations, or AI provider settings.

## Scope

### In scope

| Area | Description |
| --- | --- |
| Knowledge base administration | Create, read, update, archive, restore, and delete knowledge bases within a workspace |
| Folder hierarchy | Nested folders with move, rename, archive, and restore |
| Document lifecycle | Register documents, upload files, create versions, update metadata, move, archive, restore, delete |
| Upload orchestration | Single and bulk upload initiation, part upload, completion, and cancellation |
| Version management | Immutable version history, processing status, and current-version pointer |
| Metadata | Title, language, classification, tags, and custom metadata within policy |
| Status transitions | Draft, active, archived, deleted states per approved entity lifecycles |
| Authorization assumptions | Workspace-scoped permissions and resource ACL evaluation (enforced when identity is available) |
| Audit triggers | Archive, delete, restore, and version publication events |

### Out of scope (this spec)

| Area | Owner spec / context |
| --- | --- |
| Chunking, embedding, vector index | Knowledge Indexing (future spec) |
| Retrieval configuration | Retrieval Configuration |
| Chat and citations | Conversational Experience |
| User authentication and membership | Identity and Tenant Administration |
| OCR execution | Future integration via `IntegrationConnector` |
| External connector sync | Future Integrations |
| Full-text search API | Retrieval / search surface (future spec) |

## Goals

1. Provide a stable, tenant-safe API for organizing enterprise knowledge before RAG consumption.
2. Preserve immutable document version history with explicit lineage for citations and audit.
3. Support hierarchical browsing and bulk ingestion for operational teams.
4. Enforce authorization and classification before any content exposure.
5. Emit well-defined domain events so indexing pipelines can process content asynchronously.
6. Align all contracts with the platform response envelope and error model.

## Non-goals

- Implementing search, chat, or answer generation.
- Replacing a full enterprise content management system (ECM).
- Real-time collaborative editing of document content.
- Automatic translation or multilingual generation (metadata only in v1).
- Legal hold workflow UI (policy hooks only; full workflow is future).
- Cross-workspace knowledge federation.

## Business rules

### Tenancy and ownership

| Rule | Description |
| --- | --- |
| KB-01 | Every knowledge object carries `organization_id` and `workspace_id` denormalized for tenant-safe queries. |
| KB-02 | A knowledge base belongs to exactly one workspace; documents cannot move across knowledge bases in v1. |
| KB-03 | Folder and document names are unique among active siblings within the same parent folder (or KB root). |
| KB-04 | Creator identity is recorded for audit but does not override workspace ownership. |

### Hierarchy

| Rule | Description |
| --- | --- |
| KB-05 | Folder depth is limited (default maximum: 20 levels). |
| KB-06 | A document resides in exactly one folder or the knowledge base root. |
| KB-07 | Moving a folder moves its subtree; documents inherit effective folder path. |
| KB-08 | Archived folders cannot accept new documents or child folders. |

### Documents and versions

| Rule | Description |
| --- | --- |
| KB-09 | A document has one logical identity (`Document`) and many immutable `DocumentVersion` rows. |
| KB-10 | Version numbers are monotonic integers per document starting at 1. |
| KB-11 | Only one version is designated `current` for management views; retrieval may pin a specific version. |
| KB-12 | Upload creates a new `DocumentVersion` in `uploaded` state; processing is asynchronous. |
| KB-13 | Publishing a successfully indexed version transitions the document to `active` if it was `draft`. |
| KB-14 | Replacing file content always creates a new version; in-place binary mutation is forbidden. |

### Status and deletion

| Rule | Description |
| --- | --- |
| KB-15 | `archived` objects are read-only for content mutation; restore returns them to `active`. |
| KB-16 | `deleted` is a soft-delete terminal state for active use; rows remain for audit and citation lineage. |
| KB-17 | Archiving a knowledge base archives all folders and documents within it. |
| KB-18 | Deleting a document requires `document:delete`; legal hold blocks delete if present. |
| KB-19 | Workspace `archived` blocks new uploads and knowledge base creation. |

### Uploads and files

| Rule | Description |
| --- | --- |
| KB-20 | Supported formats in v1: `pdf`, `docx`, `txt`, `md`, `html` (native text extraction). |
| KB-21 | Maximum single file size: 50 MB (configurable per organization policy). |
| KB-22 | Bulk upload supports up to 100 files per batch (configurable). |
| KB-23 | Upload sessions expire after 24 hours if not completed. |
| KB-24 | Content hash (SHA-256) is stored per version for deduplication hints and integrity. |

### Authorization

| Rule | Description |
| --- | --- |
| KB-25 | All operations require resolved workspace membership and applicable role permission. |
| KB-26 | `document:read` is required to view metadata; binary download requires `document:download`. |
| KB-27 | Classification `restricted` or higher requires explicit document ACL or knowledge admin role. |
| KB-28 | Archived and deleted objects remain hidden from unauthorized principals even if IDs are known. |

### Indexing handoff

| Rule | Description |
| --- | --- |
| KB-29 | Knowledge Management never writes chunks or embeddings directly. |
| KB-30 | `DocumentVersionExtracted` (or equivalent) is emitted when extraction completes; indexing subscribes. |
| KB-31 | Knowledge base may enter `reindexing` when platform policy changes; that transition is coordinated externally. |

## Future extensions

| Extension | Impact on this capability |
| --- | --- |
| OCR ingestion | New `extraction_method = ocr`; additional upload content types (`png`, `jpg`, scanned PDF) |
| External connectors | `source_type = connector`; documents created by sync jobs, not direct upload |
| Multilingual segments | `declared_language` plus per-segment language maps on versions |
| Smart folders | Virtual folder type filtering documents by metadata |
| Legal hold | `legal_hold` flag blocking delete and forced purge |
| Cross-KB move | New command with re-index and ACL migration |
| Document ACL UI | Fine-grained editors/viewers management endpoints |
| Federated read-only KB | Shared corpus reference without content duplication |
| URL / wiki sources | `source_type = url` with scheduled refresh versions |

## Related documents

| Document | Purpose |
| --- | --- |
| [API.md](API.md) | HTTP contract |
| [DATABASE.md](DATABASE.md) | Persistence design |
| [WORKFLOWS.md](WORKFLOWS.md) | Process flows |
| [VALIDATION.md](VALIDATION.md) | Command validation rules |
| [ACCEPTANCE.md](ACCEPTANCE.md) | Business acceptance criteria |
| [../../docs/domain/DOMAIN_MODEL.md](../../docs/domain/DOMAIN_MODEL.md) | Approved domain |
| [../../docs/data/AGGREGATES.md](../../docs/data/AGGREGATES.md) | Aggregate boundaries |
| [../../docs/backend/API_FOUNDATION.md](../../docs/backend/API_FOUNDATION.md) | Response envelope |

## Open questions

| ID | Question | Default assumption |
| --- | --- | --- |
| OQ-01 | Should duplicate file hash within the same KB warn or block? | Warn on upload; allow with confirmation flag |
| OQ-02 | Default root folder visibility for new KBs? | Single implicit root; no physical root folder row |
| OQ-03 | Bulk upload partial failure behavior? | Per-file result summary; successful files persist |
