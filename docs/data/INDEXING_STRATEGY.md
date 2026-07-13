# Indexing Strategy

> **Status:** Accepted — implementation-ready indexing design.  
> **Purpose:** Recommend PostgreSQL and pgvector indexes without writing SQL.

## 1. Indexing principles

| Principle | Application |
| --- | --- |
| Tenant-first filtering | Leading index columns are tenant scope keys |
| Write scalability | Prefer UUIDv7 for clustered insert locality |
| Query predictability | Index for known access paths, not hypothetical ones |
| Partial indexes | Use status-filtered indexes for active rows |
| Vector separation | Keep metadata filters in PostgreSQL B-tree; vectors in pgvector |
| Measure before exotic indexes | Add GIN, expression, or partial indexes after query evidence |

## 2. Global indexing conventions

### Primary keys

- Every table has a primary key index on `id` (UUIDv7).
- No separate serial surrogate keys.

### Foreign keys

- Index every foreign key used in joins or cascade checks.
- Composite FK lookups include tenant keys when present.

### Timestamps

- Index `created_at` on high-volume append tables for retention and reporting jobs.
- Index `(status, updated_at)` on workflow tables under background workers.

### Soft delete

- Partial indexes exclude rows where `deleted_at IS NOT NULL` for hot paths.

## 3. PostgreSQL indexes by entity group

### Tenant administration

| Table | Index type | Columns | Purpose |
| --- | --- | --- | --- |
| `organization` | unique | `slug` | Tenant resolution |
| `workspace` | composite | `(organization_id, slug)` | Unique workspace slug per org |
| `workspace` | composite | `(organization_id, status)` | Active workspace listing |
| `user` | unique | `email` | Login lookup |
| `membership` | composite unique | `(organization_id, user_id, workspace_id)` | One membership per scope |
| `membership` | composite | `(workspace_id, status)` | Workspace member listing |
| `role` | composite | `(organization_id, name)` | Role lookup |

### Knowledge content

| Table | Index type | Columns | Purpose |
| --- | --- | --- | --- |
| `knowledge_base` | composite | `(organization_id, workspace_id, status)` | Workspace KB listing |
| `folder` | composite | `(knowledge_base_id, parent_folder_id, name)` | Sibling uniqueness |
| `folder` | composite | `(knowledge_base_id, path)` | Path lookup |
| `document` | composite | `(knowledge_base_id, folder_id, status)` | Folder browsing |
| `document` | composite | `(organization_id, workspace_id, status, updated_at)` | Tenant document admin views |
| `document` | composite | `(knowledge_base_id, declared_language, status)` | Language-filtered management |
| `document_version` | composite unique | `(document_id, version_number)` | Version ordering |
| `document_version` | composite | `(document_id, processing_status)` | Pipeline workers |
| `document_version` | composite | `(knowledge_base_id, processing_status, created_at)` | KB ingestion queue |
| `document_acl` | composite | `(document_id, principal_type, principal_id)` | ACL evaluation |

### Indexing artifacts

| Table | Index type | Columns | Purpose |
| --- | --- | --- | --- |
| `chunk` | composite unique | `(document_version_id, sequence_number)` | Chunk ordering |
| `chunk` | composite | `(knowledge_base_id, status, language)` | Retrieval pre-filter |
| `chunk` | composite | `(organization_id, knowledge_base_id, status)` | Tenant-safe chunk scans |
| `embedding` | composite unique | `(chunk_id, embedding_model_id, generation)` | Multiple model support |
| `embedding` | composite | `(knowledge_base_id, embedding_model_id, index_status)` | Re-index jobs |
| `embedding` | composite | `(organization_id, index_status, updated_at)` | Worker scheduling |

### Retrieval and AI configuration

| Table | Index type | Columns | Purpose |
| --- | --- | --- | --- |
| `retrieval_configuration` | composite | `(knowledge_base_id, status, version)` | Active config lookup |
| `prompt_template` | composite unique | `(organization_id, name, locale, version)` | Version resolution |
| `prompt_template` | composite | `(organization_id, status, locale)` | Active prompt listing |
| `llm_provider` | composite unique | `(provider_type, model_key)` | Catalog lookup |
| `embedding_model` | composite unique | `(provider_key, model_key)` | Catalog lookup |
| `organization_llm_provider` | composite unique | `(organization_id, llm_provider_id)` | Enablement |
| `organization_embedding_model` | composite unique | `(organization_id, embedding_model_id)` | Enablement |

### Conversational experience

| Table | Index type | Columns | Purpose |
| --- | --- | --- | --- |
| `conversation` | composite | `(workspace_id, user_id, status, updated_at)` | User conversation list |
| `conversation` | composite | `(organization_id, workspace_id, created_at)` | Admin reporting |
| `message` | composite | `(conversation_id, created_at)` | Message history |
| `message` | composite | `(conversation_id, generation_status)` | Worker recovery |
| `citation` | composite | `(message_id, rank)` | Citation order |
| `citation` | composite | `(chunk_id)` | Reverse lineage / feedback analysis |
| `feedback` | composite | `(message_id, created_at)` | Message feedback lookup |
| `feedback` | composite | `(organization_id, review_status, created_at)` | Triage queue |

### Quality and integrations

| Table | Index type | Columns | Purpose |
| --- | --- | --- | --- |
| `evaluation` | composite | `(organization_id, knowledge_base_id, status)` | Evaluation management |
| `integration_connector` | composite | `(workspace_id, connector_type, status)` | Connector admin |
| `tool_definition` | composite unique | `(integration_connector_id, tool_key, version)` | Tool resolution |
| `audit_log` | composite | `(organization_id, created_at)` | Audit queries |
| `domain_event_outbox` | composite | `(status, created_at)` | Outbox dispatcher |

## 4. Search indexes

### Full-text search (future hybrid retrieval)

| Table | Index type | Columns | Purpose |
| --- | --- | --- | --- |
| `chunk` | GIN full-text | derived `search_vector` from chunk text | Lexical retrieval |
| `document` | GIN full-text | `title` and metadata | Admin search |
| `message` | GIN full-text optional | `content` | Support search across conversations for authorized admins only |

Full-text indexes are optional in phase one but reserved for hybrid retrieval and admin search.

### JSON policy indexes

| Table | Index type | Columns | Purpose |
| --- | --- | --- | --- |
| `retrieval_configuration` | GIN | `ranking_policy` | Policy inspection |
| `tool_definition` | GIN | `input_schema` | Tool discovery |

Use JSON indexes only for operational tooling, not hot retrieval paths.

## 5. pgvector strategy

### Vector column placement

| Approach | Recommendation |
| --- | --- |
| Same row as `embedding` metadata | Preferred initially for simplicity |
| Separate `embedding_vector` table | Adopt if row width or vacuum pressure requires separation |

### Vector index types

| Index type | When to use |
| --- | --- |
| HNSW | Primary approximate nearest-neighbor search for production retrieval |
| IVFFlat | Alternative for memory-constrained environments after training lists |

**Recommendation:** Default to **HNSW** for enterprise RAG workloads with growing corpora.

### Vector index keys

Each vector index is logically scoped by:

- `organization_id`
- `knowledge_base_id`
- `embedding_model_id`
- active `index_status`

**Do not** build one global vector index across tenants.

### Recommended vector indexes

| Index | Scope | Purpose |
| --- | --- | --- |
| HNSW on embedding vector | `(knowledge_base_id, embedding_model_id)` filtered active rows | Semantic retrieval |
| Optional IVFFlat backup index | non-production or migration environments | Cost-sensitive testing |

### pgvector filter pattern

Retrieval queries should:

1. filter by tenant and authorized knowledge bases using B-tree indexes,
2. filter by `language`, `classification`, and `status`,
3. execute vector similarity over the remaining candidate set.

This matches ADR-003: relational metadata and vector similarity share a datastore but authorization happens before ranking.

## 6. Unique indexes

| Entity | Unique constraint |
| --- | --- |
| `Organization.slug` | platform-wide |
| `Workspace (organization_id, slug)` | per organization |
| `User.email` | platform-wide among active users |
| `DocumentVersion (document_id, version_number)` | per document |
| `Chunk (document_version_id, sequence_number)` | per version |
| `Embedding (chunk_id, embedding_model_id, generation)` | per model generation |
| `PromptTemplate (organization_id, name, locale, version)` | per org |
| `ToolDefinition (integration_connector_id, tool_key, version)` | per connector |
| `Membership (organization_id, user_id, workspace_id)` | per scope |

## 7. Tenant indexes (mandatory pattern)

Every tenant-owned table with more than low volume should include a composite index beginning with:

1. `organization_id`
2. `workspace_id` when applicable
3. `knowledge_base_id` when applicable

This supports:

- row-level security predicates,
- partition pruning in future,
- admin dashboards,
- background job partitioning.

## 8. Re-indexing and migration indexes

During embedding model migration, additional indexes support worker efficiency:

| Table | Index | Purpose |
| --- | --- | --- |
| `embedding` | `(embedding_model_id, index_status, knowledge_base_id)` | stale detection |
| `document_version` | `(knowledge_base_id, processing_status)` | backlog selection |
| `chunk` | `(document_version_id, status)` | superseded chunk cleanup |
| `knowledge_base` | `(status)` where `reindexing` | monitor active migrations |

## 9. Index lifecycle management

| Activity | Policy |
| --- | --- |
| Add index | Through migration with concurrency-safe strategy in implementation phase |
| Rebuild vector index | Triggered by model/dimension change or corpus scale threshold |
| Drop index | Only after query plan evidence and ADR/spec approval |
| Monitor | Track bloat, unused indexes, and sequential scan rates |

## 10. Related documents

- [Data Architecture](DATA_ARCHITECTURE.md)
- [Storage Strategy](STORAGE_STRATEGY.md)
- [Data Lifecycle](DATA_LIFECYCLE.md)
