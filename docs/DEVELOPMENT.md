# Development Guide

This guide defines the supported local setup and daily workflow for RAG-enterprise.
Run package commands from the package directory shown; the repository intentionally
has no root Python virtual environment or root Node workspace.

## Prerequisites

- Git
- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- Node.js 20 or newer and npm
- Docker Desktop or Docker Engine with Docker Compose v2

Verify the tools:

```bash
git --version
uv --version
node --version
npm --version
docker --version
docker compose version
```

## Initial configuration

From the repository root, create a local environment file:

```bash
# macOS/Linux/Git Bash
cp .env.example .env
```

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

`.env` is ignored by Git. Keep only safe placeholders in `.env.example`; never
commit credentials or production configuration.

## Docker setup

The root Compose file starts PostgreSQL with pgvector and Redis for local development:

```bash
docker compose up -d
docker compose ps
```

The convenience scripts perform the same setup:

```bash
./scripts/dev-up.sh
```

```powershell
.\scripts\dev-up.ps1
```

Inspect service logs with `docker compose logs <service>`. Stop containers with
`docker compose down`. Add `--volumes` only when you intentionally want to delete
local database and Redis data.

## Backend setup

All Python commands run from `backend/`. `uv sync` creates `backend/.venv` and uses
the committed lockfile:

```bash
cd backend
uv sync
uv run uvicorn rag_enterprise.main:app --reload --host 0.0.0.0 --port 8000
```

Verify `http://localhost:8000/api/v1/health`. Development OpenAPI documentation is
available at `http://localhost:8000/docs`.

When dependencies change, use `uv add <package>` or `uv remove <package>` from
`backend/` and commit both `pyproject.toml` and `uv.lock`.

## Frontend setup

All Node commands run from `frontend/`:

```bash
cd frontend
npm ci
npm run dev
```

Open the URL printed by Vite (normally `http://localhost:5173`). `npm ci` is the
reproducible default because `package-lock.json` is committed. Use `npm install
<package>` only when intentionally changing dependencies and commit both manifest
and lockfile.

## Testing and quality commands

Backend:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Use `uv run ruff format .` to format backend files.

Frontend:

```bash
cd frontend
npm run lint
npm run format:check
npm run test
npm run build
```

Use `npm run format` to format frontend files and `npm run test:watch` during
interactive development.

The Unix helper `./scripts/lint-and-test.sh` runs the principal backend and frontend
checks. CI remains authoritative and may add platform or security checks.

## Development workflow

1. Update local `main` and create a short-lived branch such as
   `feat/<scope>`, `fix/<scope>`, `docs/<scope>`, or `chore/<scope>`.
2. Read the relevant `specs/`, `.cursor/rules/`, agent instructions, and ADRs before
   changing code.
3. Add or update a feature specification before implementing new behavior. Add an
   ADR for durable, cross-cutting, or difficult-to-reverse decisions.
4. Implement the smallest coherent change within package boundaries. Use dependency
   injection and do not mix unrelated refactoring.
5. Add tests for success, boundary, and failure behavior; run package checks locally.
6. Update documentation and contracts in the same change.
7. Review staged files for secrets, generated artifacts, and accidental unrelated changes.
8. Use Conventional Commits and open a pull request using the repository template.
9. Address reviews, keep CI green, and obtain specialist review for architecture,
   database, infrastructure, security, or AI changes.

## Troubleshooting

- If backend imports fail, confirm commands run from `backend/` through `uv run`.
- If dependencies drift, rerun `uv sync` or `npm ci`; do not edit lockfiles manually.
- If ports 5432, 6379, 8000, or 5173 are occupied, stop the conflicting local
  service or use documented local overrides without committing secrets.
- If Compose services are unhealthy, inspect `docker compose ps` and service logs
  before resetting volumes.
