# RAG-enterprise Backend

FastAPI backend application managed with [uv](https://docs.astral.sh/uv/).

## Setup

```bash
uv sync
```

Creates `.venv` in this directory (not at monorepo root).

## Run

```bash
uv run uvicorn rag_enterprise.main:app --reload --host 0.0.0.0 --port 8000
```

## Quality

```bash
uv run ruff check .
uv run ruff format .
uv run mypy src
uv run pytest
```
