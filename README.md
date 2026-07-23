# RAG-enterprise

![Version](https://img.shields.io/badge/version-1.0.0-0F766E)

Production-grade **Retrieval-Augmented Generation** platform (monorepo).

**Version 1.0.0** delivers knowledge management, dense retrieval, grounded chat with
citations, offline evaluation, an operator console, and a public Persian demo
corpus. Durable decisions live in ADRs; detailed behavior lives in `specs/`.

Release notes: [RELEASE_NOTES.md](RELEASE_NOTES.md) · Changelog: [CHANGELOG.md](CHANGELOG.md)

## Documentation (two clicks max)

Start at the **[Documentation index](docs/README.md)** — every major guide is
linked from there. Direct shortcuts:

| Guide | Link |
| --- | --- |
| Project Overview | [docs/OVERVIEW.md](docs/OVERVIEW.md) |
| Architecture | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Architecture Summary | [docs/ARCHITECTURE_SUMMARY.md](docs/ARCHITECTURE_SUMMARY.md) |
| Feature Map | [docs/FEATURE_MAP.md](docs/FEATURE_MAP.md) |
| Development Guide | [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) |
| Development Workflow | [docs/DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md) |
| Deployment Guide | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| Evaluation Guide | [docs/EVALUATION_GUIDE.md](docs/EVALUATION_GUIDE.md) |
| Demo Guide | [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) |
| ADR index | [docs/DECISIONS.md](docs/DECISIONS.md) |

## Repository structure

```text
RAG-enterprise/
├── backend/          # FastAPI application (Python, uv)
├── frontend/         # React + Vite + TypeScript operator console
├── demo/             # Official V1 Persian demo corpus (RC1.4)
├── infrastructure/   # IaC placeholder; local Compose at repo root
├── docs/             # Guides, architecture, domain/data docs
├── specs/            # Feature specifications (authoritative)
├── scripts/          # Developer and CI helpers
├── tests/            # Cross-cutting integration tests (placeholder)
├── agents/           # AI-assisted development agent definitions
├── .cursor/rules/    # Cursor IDE project rules
└── .github/workflows/# CI pipelines
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 20+ and npm
- Docker and Docker Compose

Expanded checklist: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#prerequisites).

## Quick start

**One command** (after `.env` + `backend/.env` exist — copy from `.env.example` once):

```bash
uv run python run.py
```

This starts Docker (Postgres/Redis), migrations, backend, and frontend. Details:
[docs/FIRST_RUN.md](docs/FIRST_RUN.md).

Manual minimal path (if you prefer separate terminals): see
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

### Infrastructure only

```bash
cp .env.example .env
docker compose up -d
```

### Backend only

```bash
cd backend
uv sync
uv run uvicorn rag_enterprise.main:app --reload --host 0.0.0.0 --port 8000
```

- Liveness: <http://localhost:8000/api/v1/live>
- Readiness: <http://localhost:8000/api/v1/ready>
- OpenAPI: <http://localhost:8000/docs>

### Frontend only

```bash
cd frontend
npm ci
npm run dev
```

Open the URL printed by Vite (normally <http://localhost:5173>).

### Try the demo

Import `demo/knowledge/`, index, and chat — see [Demo Guide](docs/DEMO_GUIDE.md).

## Development quality

| Area | Lint | Test | Format |
| --- | --- | --- | --- |
| Backend | `uv run ruff check` | `uv run pytest` | `uv run ruff format` |
| Frontend | `npm run lint` | `npm run test` | `npm run format` |

- Workflow: [docs/DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md)
- Contributing: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)

## Package entry points

| Package | README |
| --- | --- |
| Backend | [backend/README.md](backend/README.md) |
| Frontend | [frontend/README.md](frontend/README.md) |
| Specs | [specs/README.md](specs/README.md) |
| Demo | [demo/README.md](demo/README.md) |
| Infrastructure | [infrastructure/README.md](infrastructure/README.md) |

## License

[MIT](LICENSE)
