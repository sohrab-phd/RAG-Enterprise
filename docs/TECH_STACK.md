# Technology Stack

> **Release:** 1.0.0  
> **Status:** Reflects dependencies adopted for Version 1.0.0.  
> **Planned items:** marked **Version 2** (see [Roadmap](ROADMAP.md)).

## Backend

| Technology | Purpose | Status |
| --- | --- | --- |
| Python 3.12+ | Runtime | Adopted |
| uv | Package manager | Adopted |
| FastAPI | HTTP API framework | Adopted |
| Pydantic / pydantic-settings | Validation & config | Adopted |
| structlog | Structured logging | Adopted |
| SQLAlchemy 2 | ORM (async) | Adopted |
| Alembic | Migrations | Adopted |
| pgvector | Vector similarity | Adopted |
| pytest / ruff / mypy | Testing & quality | Adopted |
| LangGraph | Agent orchestration | **Version 2** |

## Frontend

| Technology | Purpose | Status |
| --- | --- | --- |
| React | UI framework | Adopted |
| Vite | Build tool | Adopted |
| TypeScript | Type safety | Adopted |
| Tailwind CSS | Styling | Adopted |
| shadcn/ui | Component library | Adopted |
| TanStack Query | Server state | Adopted |
| ESLint / Prettier | Linting & formatting | Adopted |

## Infrastructure

| Technology | Purpose | Status |
| --- | --- | --- |
| Docker Compose | Local development | Adopted |
| PostgreSQL | Primary datastore | Local (V1) |
| pgvector | Vector search extension | Local (V1) |
| Redis | Present in Compose; core RAG path does not require it | Local (V1) |
| Local filesystem | Upload / extracted text storage | Adopted |
| Multi-node production topology | Cloud/K8s IaC | **Version 2** |

## Observability

| Technology | Purpose | Status |
| --- | --- | --- |
| Structured logs + health probes | Ops visibility | Adopted |
| OpenTelemetry / Prometheus / Grafana / Sentry | Full observability stack | **Version 2** |

## CI/CD

| Technology | Purpose | Status |
| --- | --- | --- |
| GitHub Actions | CI pipelines | Adopted |

## Related documents

- [Architecture Summary](ARCHITECTURE_SUMMARY.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Roadmap](ROADMAP.md)
- [Documentation index](README.md)
