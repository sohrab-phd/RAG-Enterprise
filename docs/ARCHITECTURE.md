# Architecture

> **Status:** Draft skeleton — TODO: document system architecture as features are implemented.

## 1. Architectural Principles

<!-- TODO: Modularity, async-first, observability, security-by-default -->

## 2. High-Level System Context

<!-- TODO: C4 context diagram and narrative -->

## 3. Monorepo Layout

<!-- TODO: Describe backend, frontend, infrastructure boundaries -->

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

<!-- TODO: React app structure, state management, API client -->

## 6. Data Architecture

<!-- TODO: PostgreSQL, pgvector, Redis roles -->

## 7. AI / RAG Pipeline (Future)

<!-- TODO: LangGraph orchestration, embedding strategy, retrieval -->

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

<!-- TODO: Metrics and distributed tracing -->

## 9. Security Architecture

<!-- TODO: AuthN/AuthZ, secrets, network boundaries -->

## 10. Deployment Topology (Future)

<!-- TODO: Environments, CI/CD, infrastructure as code -->
