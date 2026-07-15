# Deployment Guide

> **Purpose:** How Version 1.0.0 is run today and what is deliberately deferred.  
> **Release:** 1.0.0  
> **Status:** Local Docker Compose is supported; production IaC is not yet shipped.

## Purpose

Point operators at the supported local deployment path and the documents that will
grow when production topology lands—without inventing undocumented cloud procedures.

## Audience

Developers and operators bringing up a local stack.

## Local deployment (supported)

1. Copy environment: `.env.example` → `.env` (never commit secrets).
2. Start PostgreSQL (pgvector) and Redis via root Compose:

   ```bash
   docker compose up -d
   docker compose ps
   ```

   Helpers: `./scripts/dev-up.sh` or `.\scripts\dev-up.ps1`.
3. Run the API from `backend/` and the console from `frontend/` — see
   [Development Guide](DEVELOPMENT.md) and [Quick Start](../README.md#quick-start).
4. Verify probes: [Operational Health](backend/OPERATIONAL_HEALTH.md)
   (`/api/v1/live`, `/api/v1/ready`).

Service inventory: [infrastructure/README.md](../infrastructure/README.md).

## Configuration

Startup validation (fail fast): [CONFIGURATION.md](backend/CONFIGURATION.md).

LLM backends (`local` / `api` / `mock`): [LLM Provider Layer (RC2.6)](backend/LLM_PROVIDER_LAYER.md).
Local Ollama: [OLLAMA.md](backend/OLLAMA.md).
V1 defaults to **local** (Ollama). Prefer `mock` in CI; use `api` for OpenAI-compatible
remote models. Legacy `echo`/`http` remap automatically with a startup warning.

Application settings are documented alongside Compose variables in `.env.example`.
Upload binaries persist under `FILE_STORAGE_ROOT` (default `storage/uploads`);
see [Local File Storage](backend/LOCAL_FILE_STORAGE.md).

## Production (Version 2)

Multi-node production topology, secret managers, and environment overlays are
**Version 2**. Version 1.0.0 supports local single-node Compose + process hosts.

Placeholders:

- [infrastructure/README.md](../infrastructure/README.md)
- [ARCHITECTURE.md §Deployment Topology](ARCHITECTURE.md#10-deployment-topology)
- [Architecture Summary](ARCHITECTURE_SUMMARY.md)
- [Roadmap](ROADMAP.md)

Do not treat local Compose credentials as production-ready.

## Related documents

- [Development Guide](DEVELOPMENT.md)
- [Operational Health](backend/OPERATIONAL_HEALTH.md)
- [Tech Stack](TECH_STACK.md)
- [Documentation index](README.md)
