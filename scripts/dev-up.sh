#!/usr/bin/env bash
# Start local infrastructure services (PostgreSQL + pgvector, Redis).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  echo "Copying .env.example to .env"
  cp .env.example .env
fi

docker compose up -d
docker compose ps
