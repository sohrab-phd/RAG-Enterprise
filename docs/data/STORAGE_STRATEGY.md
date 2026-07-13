# Storage Strategy

> **Status:** Accepted — implementation-ready storage placement design.  
> **Purpose:** Specify where each entity and payload is stored and why.

## 1. Storage tiers

| Tier | Technology | Role |
| --- | --- | --- |
| Transactional metadata | PostgreSQL | Source of truth for entities, ACLs, lineage, configuration, audit |
| Vector retrieval | PostgreSQL pgvector | Similarity search over embedding vectors with metadata filters |
| Large binaries and text | Object storage | Original files, extracted text, OCR output, evaluation datasets |
| Ephemeral acceleration | Redis | Cache, rate limits, job locks, short-lived retrieval artifacts |
| Future external storage | Connector-specific systems | Web search results, SQL warehouses, MCP remote resources |

PostgreSQL remains the system of record. Redis and external stores are never authoritative.

## 2. Storage placement by entity

| Entity | PostgreSQL | Object storage | Redis | Vector store | Future external |
| --- | --- | --- | --- | --- | --- |
| `Organization` | Yes | No | Cache policy | No | No |
| `Workspace` | Yes | No | Cache membership | No | No |
| `User` | Yes | No | Session cache | No | No |
| `Role` | Yes | No | Permission cache | No | No |
| `Membership` | Yes | No | AuthZ cache | No | No |
| `KnowledgeBase` | Yes | No | Config cache | No | No |
| `Folder` | Yes | No | No | No | No |
| `Document` | Yes metadata | No | No | No | No |
| `DocumentVersion` | Yes metadata | Yes extracted text and originals | No | No | Connector source optional |
| `Chunk` | Yes metadata | Optional large text | No | No | No |
| `Embedding` | Yes metadata | No | No | Yes pgvector column | No |
| `EmbeddingModel` | Yes | No | Cache catalog | No | No |
| `RetrievalConfiguration` | Yes | No | Cache active config | No | No |
| `LLMProvider` | Yes metadata | No | Cache catalog | No | Provider endpoint external |
| `PromptTemplate` | Yes metadata | Optional large prompt body | Cache active version | No | No |
| `Conversation` | Yes | No | No | No | No |
| `Message` | Yes | Optional large tool payloads | No | No | No |
| `Citation` | Yes | No | No | No | Optional external evidence ref |
| `Evaluation` | Yes metadata | Yes datasets and result artifacts | Job state | No | No |
| `Feedback` | Yes | No | No | No | No |
| `IntegrationConnector` | Yes metadata | No | Health cache | No | Yes remote system |
| `ToolDefinition` | Yes | No | No | No | Yes MCP/web/sql endpoints |
| `audit_log` | Yes | Archive after retention | No | No | No |
| `domain_event_outbox` | Yes | No | Dispatcher lock | No | No |
| `ingestion_job` | Yes | No | Queue state | No | No |
| `reindex_job` | Yes | No | Queue state | No | No |

## 3. Object storage layout

Object keys are tenant-scoped and immutable per version.

```text
org/{organization_id}/
  workspace/{workspace_id}/
    knowledge-base/{knowledge_base_id}/
      document/{document_id}/
        version/{document_version_id}/
          original/{filename}
          extracted/text.txt
          extracted/ocr.json
          extracted/layout.json
    evaluation/{evaluation_id}/
      dataset.jsonl
      results.json
  prompt/{prompt_template_id}/v{version}/body.txt
```

### Why object storage for these payloads

| Payload | Reason |
| --- | --- |
| Original uploads | Large binaries, cheap storage, offloads PostgreSQL bloat |
| Extracted text | Can exceed row comfort size; immutable per version |
| OCR/layout JSON | Large structured output; future OCR support |
| Evaluation datasets | Versioned files consumed by offline jobs |
| Prompt bodies | Optional offload when templates are large |

## 4. PostgreSQL contents

PostgreSQL stores:

- identifiers and foreign keys,
- lifecycle status,
- ACL and classification metadata,
- tenant scope columns,
- audit columns,
- configuration JSON within size limits,
- citation and lineage references,
- modest message text if policy allows,
- pgvector columns or companion vector table.

PostgreSQL does **not** store:

- provider secrets,
- raw uploaded binaries,
- full evaluation corpora by default,
- long-term ephemeral web search HTML.

## 5. Redis usage

| Use case | Key pattern | TTL | Why |
| --- | --- | --- | --- |
| Membership and permission cache | `authz:org:{id}:user:{id}` | short | Reduce auth latency |
| Active retrieval config | `retrieval:kb:{id}:active` | medium | Fast chat startup |
| Rate limits | `ratelimit:org:{id}:...` | rolling | Noisy-neighbor control |
| Ingestion/reindex job lock | `joblock:{type}:{id}` | short | Worker coordination |
| Ephemeral web evidence future | `evidence:conv:{id}:{hash}` | minutes | Non-authoritative augmentation |
| Conversation streaming state | `stream:msg:{id}` | minutes | UI streaming only |

Redis loss must never cause data loss or authorization expansion.

## 6. Vector store strategy

| Aspect | Decision |
| --- | --- |
| Initial vector store | pgvector inside PostgreSQL |
| Vector payload | `embedding` row or child table |
| Metadata filters | PostgreSQL columns on `chunk` and `embedding` |
| Future dedicated vector DB | Optional migration path; preserve lineage in PostgreSQL |

pgvector is chosen to keep ACL filtering and vector search in one transactional system, consistent with ADR-003.

## 7. Future external storage

| Capability | Storage choice | Authority |
| --- | --- | --- |
| OCR service output | Object storage + `DocumentVersion` metadata | Platform |
| Web search results | Redis or object storage ephemeral bucket | Non-authoritative |
| SQL agent result sets | External warehouse + ephemeral result cache | Non-authoritative unless saved as document |
| MCP remote resources | External MCP server | Non-authoritative; tool output validated then optionally ingested |
| Long-term audit archive | Object storage or cold storage | Read-only compliance archive |

External results become authoritative only if explicitly ingested into `Document` / `DocumentVersion`.

## 8. Multilingual storage

| Data | Storage approach |
| --- | --- |
| `declared_language` on `Document` | PostgreSQL column |
| `language` on `Chunk` | PostgreSQL column |
| `locale` on `PromptTemplate` and `Conversation` | PostgreSQL columns |
| multilingual segment maps future | Object storage JSON linked from `DocumentVersion` |

Language is metadata in PostgreSQL; language-specific content bodies remain with version artifacts.

## 9. Multiple providers and models

| Asset | Storage |
| --- | --- |
| Provider catalog | PostgreSQL |
| Org enablement | PostgreSQL join tables |
| Provider secrets | Secret manager; only secret reference in PostgreSQL |
| Model defaults | PostgreSQL JSON on provider rows |
| Embedding vectors | pgvector keyed by `embedding_model_id` |

This allows multiple models per chunk through separate `Embedding` rows.

## 10. Backup and residency

| Tier | Backup | Residency |
| --- | --- | --- |
| PostgreSQL | PITR and nightly snapshots | Organization `data_residency_policy` |
| Object storage | Versioned bucket replication | Same region as tenant policy |
| Redis | No durable backup requirement | Same region |
| pgvector | Backed up with PostgreSQL | Same region |

## 11. Related documents

- [Data Architecture](DATA_ARCHITECTURE.md)
- [Indexing Strategy](INDEXING_STRATEGY.md)
- [Data Lifecycle](DATA_LIFECYCLE.md)
