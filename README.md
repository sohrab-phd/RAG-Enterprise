# RAG-enterprise

Production-grade Retrieval-Augmented Generation (RAG) platform monorepo.

This repository establishes the foundational skeleton for long-lived enterprise development. Business features (authentication, RAG pipelines, chat, agents) are intentionally deferred to future work.

## Repository structure

```
RAG-enterprise/
├── backend/          # FastAPI application (Python, uv)
├── frontend/         # React + Vite + TypeScript
├── demo/             # Official V1 Persian demo corpus (RC1.4)
├── infrastructure/   # IaC and deployment assets (future)
├── docs/             # Architecture and product documentation
├── specs/            # Feature specifications
├── scripts/          # Developer and CI helper scripts
├── tests/            # Cross-cutting integration tests (future)
├── agents/           # AI-assisted development agent definitions
├── .cursor/rules/    # Cursor IDE project rules
└── .github/workflows/# CI/CD pipelines
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 20+ and npm
- Docker and Docker Compose

## Quick start

### 1. Infrastructure

```bash
cp .env.example .env
docker compose up -d
```

### 2. Backend

```bash
cd backend
uv sync
uv run uvicorn rag_enterprise.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

## Development

| Area        | Lint              | Test           | Format          |
|-------------|-------------------|----------------|-----------------|
| Backend     | `uv run ruff check` | `uv run pytest` | `uv run ruff format` |
| Frontend    | `npm run lint`    | `npm run test` | `npm run format` |

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for contribution guidelines.

## Documentation

- [Product Requirements](docs/PRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Tech Stack](docs/TECH_STACK.md)
- [Roadmap](docs/ROADMAP.md)
- [Architecture Decisions](docs/DECISIONS.md)
- [Official Demo Workspace (V1)](demo/README.md)

## License

[MIT](LICENSE)
