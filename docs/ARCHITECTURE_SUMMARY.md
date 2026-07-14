# Architecture Summary

> **Purpose:** One-page Version 1.0.0 architecture map.  
> **Release:** 1.0.0  
> **Rule:** Summarize with links—do not copy ADR or spec prose here.

## Purpose

Describe how the monorepo fits together for Version 1.0.0: API runtime, data stores,
RAG pipeline boundaries, and where durable decisions live.

## Runtime sketch

```text
Operator console (frontend)
        │  HTTP /api/v1
        ▼
FastAPI app (create_app + lifespan)
  ├─ RC1.1 configuration validation
  ├─ Structured logging
  ├─ AppContainer (DB, storage, providers, services)
  └─ Routes: knowledge · retrieve · chat · evaluations · health
        │
        ▼
PostgreSQL (+ pgvector)     Redis (local / future)
Evaluation artifacts (filesystem)
```

Process lifecycle and health endpoints:
[Architecture notes §Backend](ARCHITECTURE.md#4-backend-architecture) and
[Operational Health](backend/OPERATIONAL_HEALTH.md).

## RAG pipeline (Version 1.0.0)

```text
001 Knowledge → 002 Process* → 003 Chunk* → 004 Embed → 005 Retrieve → 006 Generate
                                                                         ↑
                                                              007 Evaluation
```

\*Processing/chunking HTTP workers are still maturing; see
[E2E Happy Path](backend/E2E_HAPPY_PATH.md) and [Feature Map](FEATURE_MAP.md).

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

## Related documents

- [Project Overview](OVERVIEW.md)
- [Feature Map](FEATURE_MAP.md)
- [Tech Stack](TECH_STACK.md)
- [Documentation index](README.md)
