# Architecture

> **Status:** Evolving runtime notes for Version 1.0.0.  
> **Prefer:** [Architecture Summary](ARCHITECTURE_SUMMARY.md) for the V1.0.0 map and ADR index.

This page records implementation-facing architecture notes as they land. Durable
decisions remain in [DECISIONS.md](DECISIONS.md) / `docs/adr/`. Feature behavior
remains in `specs/`.

## 1. Architectural Principles

See [ADR 001](adr/001-monorepo-architecture.md) and
[ADR 005](adr/005-ai-platform-principles.md). Governance:
[`.cursor/rules/architecture.md`](../.cursor/rules/architecture.md).

## 2. High-Level System Context

Operator console → FastAPI `/api/v1` → PostgreSQL/pgvector, local filesystem storage
(+ Redis in local Compose). Narrative map:
[Architecture Summary](ARCHITECTURE_SUMMARY.md).

## 3. Monorepo Layout

Package boundaries: [Project Overview](OVERVIEW.md) and
[ADR 001](adr/001-monorepo-architecture.md).

## 4. Backend Architecture

FastAPI application factory (`rag_enterprise.main.create_app`) wires middleware,
exception handlers, OpenAPI, and the `/api/v1` router. Process lifecycle is owned
by `rag_enterprise.lifespan.lifespan`:

1. Load `Settings`.
2. Run configuration validation (fail fast with grouped stderr report).
3. Configure structured logging.
4. Initialize `AppContainer` (DB engine, `FileSystemStorage`, providers, services).
5. Serve requests; dispose resources on shutdown.

See [CONFIGURATION.md](backend/CONFIGURATION.md),
[API Foundation](backend/API_FOUNDATION.md),
[Local File Storage](backend/LOCAL_FILE_STORAGE.md), and
[Operational Health](backend/OPERATIONAL_HEALTH.md).

## 5. Frontend Architecture

Operator console notes: [frontend/README.md](../frontend/README.md) ·
[Feature 008](../specs/008-frontend/README.md).

## 6. Data Architecture

Entry points: [data/DATA_ARCHITECTURE.md](data/DATA_ARCHITECTURE.md) ·
[ADR 003](adr/003-database-selection.md).

## 7. AI / RAG Pipeline

Version 1.0.0 pipeline map: [Feature Map](FEATURE_MAP.md) ·
[Architecture Summary](ARCHITECTURE_SUMMARY.md#rag-pipeline-version-100).

Implemented operator surfaces:

- **Publish** knowledge bases (`draft` → `active`) —
  [KNOWLEDGE_MANAGEMENT.md](backend/KNOWLEDGE_MANAGEMENT.md)
- **Process & Index** (synchronous orchestration) —
  [PROCESS_AND_INDEX.md](backend/PROCESS_AND_INDEX.md)

LangGraph / agent-tool orchestration is **Version 2**
([Roadmap](ROADMAP.md), [ADR 005](adr/005-ai-platform-principles.md)).

## 8. Observability

Structured logging is configured at startup (`rag_enterprise.core.logging`).
Operational probes (no auth) under `/api/v1`:

| Path | Role |
| --- | --- |
| `GET /live` | Process liveness — no dependency checks |
| `GET /ready` | Readiness — config flag, DI, DB, evaluation + upload storage |
| `GET /system` | Inventory — version, env, provider/model names, entity counts |
| `GET /health` | Legacy compatibility |

Details: [Operational Health](backend/OPERATIONAL_HEALTH.md).

Automated golden-path E2E:
[End-to-End Happy Path](backend/E2E_HAPPY_PATH.md).

Distributed tracing and metrics backends are **Version 2**.

## 9. Security Architecture

Authentication and hardened AuthZ are **Version 2**. Version 1.0.0 uses development
actor headers for local/demo operation.

Tenancy background: [domain/MULTI_TENANCY.md](domain/MULTI_TENANCY.md) ·
[domain/PERMISSION_MODEL.md](domain/PERMISSION_MODEL.md).

## 10. Deployment Topology

Local path today: [Deployment Guide](DEPLOYMENT.md).
Production / multi-node IaC is **Version 2** —
[infrastructure/README.md](../infrastructure/README.md).

## Related documents

- [Architecture Summary](ARCHITECTURE_SUMMARY.md)
- [Documentation index](README.md)
- [ADR index](DECISIONS.md)
- [Roadmap](ROADMAP.md)
