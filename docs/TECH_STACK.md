# Technology Stack

> **Status:** Draft skeleton — TODO: keep in sync with implemented dependencies.

## Backend

| Technology | Purpose | Status |
|------------|---------|--------|
| Python 3.12+ | Runtime | Adopted |
| uv | Package manager | Adopted |
| FastAPI | HTTP API framework | Adopted |
| Pydantic / pydantic-settings | Validation & config | Adopted |
| structlog | Structured logging | Adopted |
| SQLAlchemy 2 | ORM (async) | Planned |
| LangGraph | Agent orchestration | Planned |
| pytest / ruff / mypy | Testing & quality | Adopted |

## Frontend

| Technology | Purpose | Status |
|------------|---------|--------|
| React | UI framework | Adopted |
| Vite | Build tool | Adopted |
| TypeScript | Type safety | Adopted |
| Tailwind CSS | Styling | Adopted |
| shadcn/ui | Component library | Adopted |
| ESLint / Prettier | Linting & formatting | Adopted |

## Infrastructure

| Technology | Purpose | Status |
|------------|---------|--------|
| Docker Compose | Local development | Adopted |
| PostgreSQL | Primary datastore | Local only |
| pgvector | Vector search extension | Local only |
| Redis | Cache / queues | Local only |

## Observability (Planned)

<!-- TODO: OpenTelemetry, Prometheus, Grafana, Sentry -->

## CI/CD

| Technology | Purpose | Status |
|------------|---------|--------|
| GitHub Actions | CI pipelines | Adopted |
