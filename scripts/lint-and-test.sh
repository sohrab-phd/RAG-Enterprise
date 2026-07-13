#!/usr/bin/env bash
# Run backend and frontend quality checks from the monorepo root.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Backend: ruff"
(cd "$ROOT_DIR/backend" && uv run ruff check .)

echo "==> Backend: mypy"
(cd "$ROOT_DIR/backend" && uv run mypy src)

echo "==> Backend: pytest"
(cd "$ROOT_DIR/backend" && uv run pytest)

echo "==> Frontend: lint"
(cd "$ROOT_DIR/frontend" && npm run lint)

echo "==> Frontend: format check"
(cd "$ROOT_DIR/frontend" && npm run format:check)

echo "==> Frontend: test"
(cd "$ROOT_DIR/frontend" && npm run test)

echo "All checks passed."
