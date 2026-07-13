# Infrastructure

> **Status:** Placeholder — production deployment is intentionally deferred.

## Local Development

Local services are defined in the root `docker-compose.yml`:

| Service | Image | Purpose |
|---------|-------|---------|
| postgres | `pgvector/pgvector:pg16` | PostgreSQL with pgvector extension |
| redis | `redis:7-alpine` | Cache and message broker (future) |

## Future Contents

<!-- TODO: Terraform / Pulumi modules -->
<!-- TODO: Kubernetes manifests or ECS task definitions -->
<!-- TODO: Environment-specific overlays (staging, production) -->
<!-- TODO: Observability stack configuration -->

## Assumptions

- Local development uses Docker Compose only
- Production topology will be documented in `docs/ARCHITECTURE.md` when defined
- Secrets are never committed; use environment variables and secret managers
