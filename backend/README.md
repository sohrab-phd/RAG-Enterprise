# RAG-enterprise Backend

FastAPI backend managed with [uv](https://docs.astral.sh/uv/). Source lives in
`src/rag_enterprise/`; tests in `tests/`.

## Purpose

HTTP `/api/v1` surface for knowledge, retrieval, chat, evaluation reads, and
operational health. Business rules stay out of routers—see application and domain
docs linked below.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Local Postgres/Redis when not using sqlite test fixtures — see
  [Development Guide](../docs/DEVELOPMENT.md)

## Setup

```bash
uv sync
```

Creates `.venv` in this directory (not at monorepo root).

## Run

```bash
uv run uvicorn rag_enterprise.main:app --reload --host 0.0.0.0 --port 8000
```

- Live: `GET /api/v1/live`
- Ready: `GET /api/v1/ready`
- OpenAPI: `/docs`

## Quality

```bash
uv run ruff check .
uv run ruff format .
uv run mypy src
uv run pytest
```

## Related documents

- [Documentation index](../docs/README.md)
- [Architecture Summary](../docs/ARCHITECTURE_SUMMARY.md)
- [Feature Map](../docs/FEATURE_MAP.md)
- [API Foundation](../docs/backend/API_FOUNDATION.md)
- [Configuration](../docs/backend/CONFIGURATION.md)
- [Operational Health](../docs/backend/OPERATIONAL_HEALTH.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)
- [Root README](../README.md)
