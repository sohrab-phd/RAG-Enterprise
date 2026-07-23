# Architecture Summary

> **Purpose:** One-page Version 1.0.0 architecture map.  
> **Release:** 1.0.0  
> **Rule:** Summarize with links—do not copy ADR or spec prose here.  
> **Full narrative:** [ARCHITECTURE.md](ARCHITECTURE.md) (system flows, diagrams, decisions).

## Purpose

Describe how the monorepo fits together for Version 1.0.0: API runtime, data stores,
RAG pipeline boundaries, and where durable decisions live.

## Runtime sketch

```text
Operator console (frontend)
        │  HTTP /api/v1
        ▼
FastAPI app (create_app + lifespan)
  ├─ Configuration validation
  ├─ Structured logging
  ├─ AppContainer (DB, FileSystemStorage, providers, services)
  └─ Routes: knowledge · process · retrieve · chat · evaluations · health
        │
        ▼
PostgreSQL (+ pgvector)     Redis (local Compose; not required for core RAG path)
Local upload/extracted files (FILE_STORAGE_ROOT)
Evaluation artifacts (filesystem)
```

Process lifecycle and health endpoints:
[Architecture notes §Backend](ARCHITECTURE.md#4-backend-architecture) and
[Operational Health](backend/OPERATIONAL_HEALTH.md).

Storage: [Local File Storage](backend/LOCAL_FILE_STORAGE.md)
(`FileSystemStorage` at runtime; `InMemoryFileStorage` in tests only).

## RAG pipeline (Version 1.0.0)

```text
Create/Publish KB
  → Upload (local filesystem)
  → Process & Index (parse → normalize → chunk → embed)
  → Retrieve (hybrid dense + BM25 + RRF → RC3.2 ranking)
  → Evidence selection (RC3.6) → Generate (+ citations)
  → Offline evaluation (+ Evaluation Dashboard reads)
```

Full diagrams and rationale: [ARCHITECTURE.md](ARCHITECTURE.md).

Operator orchestration:
[Process & Index](backend/PROCESS_AND_INDEX.md) ·
[Publish workflow](backend/KNOWLEDGE_MANAGEMENT.md#knowledge-base-lifecycle).

Module docs:

- [Knowledge management](backend/KNOWLEDGE_MANAGEMENT.md)
- [Embeddings & retrieval](backend/EMBEDDINGS_AND_RETRIEVAL.md)
- [RAG generation](backend/RAG_GENERATION.md)
- [Evaluation framework](backend/EVALUATION_FRAMEWORK.md)

## Domain and data authority

| Concern | Entry |
| --- | --- |
| Bounded contexts | [BOUNDED_CONTEXTS.md](domain/BOUNDED_CONTEXTS.md) |
| Domain model | [DOMAIN_MODEL.md](domain/DOMAIN_MODEL.md) |
| Multi-tenancy | [MULTI_TENANCY.md](domain/MULTI_TENANCY.md) |
| Data architecture | [DATA_ARCHITECTURE.md](data/DATA_ARCHITECTURE.md) |
| Physical lifecycle | [DATA_LIFECYCLE.md](data/DATA_LIFECYCLE.md) |

## Architecture Decision Records

Durable decisions are indexed in [DECISIONS.md](DECISIONS.md):

| ADR | Topic |
| --- | --- |
| [001](adr/001-monorepo-architecture.md) | Monorepo layout and package boundaries |
| [002](adr/002-backend-framework-selection.md) | FastAPI / uv backend |
| [003](adr/003-database-selection.md) | PostgreSQL + pgvector |
| [004](adr/004-frontend-selection.md) | React / Vite frontend |
| [005](adr/005-ai-platform-principles.md) | AI platform principles |

Accepted ADRs are not rewritten; supersede with a new record when decisions change.

## Frontend architecture

Operator console modules and stack:
[frontend/README.md](../frontend/README.md) and
[specs/008-frontend](../specs/008-frontend/README.md).

## Deployment and observability

- Local topology: [Deployment Guide](DEPLOYMENT.md)
- Probes and inventory: [Operational Health](backend/OPERATIONAL_HEALTH.md)
- Evolving notes: [ARCHITECTURE.md](ARCHITECTURE.md) (§Observability, Security, Deployment)
- Multi-node production topology: **Version 2** ([Roadmap](ROADMAP.md))

## Related documents

- [Project Overview](OVERVIEW.md)
- [Feature Map](FEATURE_MAP.md)
- [Tech Stack](TECH_STACK.md)
- [Documentation index](README.md)
