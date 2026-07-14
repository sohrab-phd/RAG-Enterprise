# Architecture

> **Status:** Evolving runtime notes for Version 1.  
> **Prefer:** [Architecture Summary](ARCHITECTURE_SUMMARY.md) for the V1 map and ADR index.

This page records implementation-facing architecture notes as they land. Durable
decisions remain in [DECISIONS.md](DECISIONS.md) / `docs/adr/`. Feature behavior
remains in `specs/`.

## 1. Architectural Principles

See [ADR 001](adr/001-monorepo-architecture.md) and
[ADR 005](adr/005-ai-platform-principles.md). Governance:
[`.cursor/rules/architecture.md`](../.cursor/rules/architecture.md).

## 2. High-Level System Context

Operator console → FastAPI `/api/v1` → PostgreSQL/pgvector (+ Redis local).
Narrative map: [Architecture Summary](ARCHITECTURE_SUMMARY.md).

## 3. Monorepo Layout

Package boundaries: [Project Overview](OVERVIEW.md) and
[ADR 001](adr/001-monorepo-architecture.md).

## 4. Backend Architecture

FastAPI application factory (`rag_enterprise.main.create_app`) wires middleware,
exception handlers, OpenAPI, and the `/api/v1` router. Process lifecycle is owned
by `rag_enterprise.lifespan.lifespan`:

1. Load `Settings`.
2. Run RC1.1 configuration validation (fail fast with grouped stderr report).
3. Configure structured logging.
4. Initialize `AppContainer` (DB engine, providers, domain services).
5. Serve requests; dispose resources on shutdown.

See [CONFIGURATION.md](backend/CONFIGURATION.md),
[API Foundation](backend/API_FOUNDATION.md), and
[Operational Health](backend/OPERATIONAL_HEALTH.md).

## 5. Frontend Architecture

Operator console notes: [frontend/README.md](../frontend/README.md) ·
[Feature 008](../specs/008-frontend/README.md).

## 6. Data Architecture

Entry points: [data/DATA_ARCHITECTURE.md](data/DATA_ARCHITECTURE.md) ·
[ADR 003](adr/003-database-selection.md).

## 7. AI / RAG Pipeline

Version 1 pipeline map: [Feature Map](FEATURE_MAP.md) ·
[Architecture Summary](ARCHITECTURE_SUMMARY.md#rag-pipeline-version-1).
LangGraph orchestration remains future work ([ADR 005](adr/005-ai-platform-principles.md)).

## 8. Observability

Structured logging is configured at startup (`rag_enterprise.core.logging`).
RC1.2 operational probes (no auth) under `/api/v1`:

| Path | Role |
| --- | --- |
| `GET /live` | Process liveness — no dependency checks |
| `GET /ready` | Readiness — config flag, DI, DB, evaluation + upload storage |
| `GET /system` | Inventory — version, env, provider/model names, entity counts |
| `GET /health` | Legacy compatibility |

Details: [Operational Health](backend/OPERATIONAL_HEALTH.md).

RC1.3 ships one automated golden-path E2E scenario for the Persian leave-policy
pipeline: [End-to-End Happy Path](backend/E2E_HAPPY_PATH.md).

<!-- TODO: Metrics and distributed tracing -->

## 9. Security Architecture

<!-- TODO: AuthN/AuthZ, secrets, network boundaries -->

Tenancy background: [domain/MULTI_TENANCY.md](domain/MULTI_TENANCY.md) ·
[domain/PERMISSION_MODEL.md](domain/PERMISSION_MODEL.md).

## 10. Deployment Topology (Future)

Local path today: [Deployment Guide](DEPLOYMENT.md). Production IaC deferred —
[infrastructure/README.md](../infrastructure/README.md).

## Related documents

- [Architecture Summary](ARCHITECTURE_SUMMARY.md)
- [Documentation index](README.md)
- [ADR index](DECISIONS.md)
