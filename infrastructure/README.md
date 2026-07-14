# Infrastructure

> **Status:** Local Docker Compose supported; production deployment deferred.

## Purpose

Hold future IaC and document today’s local dependency stack. Runtime Compose file
lives at the **repository root** (`docker-compose.yml`), not under this folder yet.

## Local development

| Service | Image | Purpose |
| --- | --- | --- |
| postgres | `pgvector/pgvector:pg16` | PostgreSQL with pgvector |
| redis | `redis:7-alpine` | Cache / broker (future use) |

How to start and configure: [Deployment Guide](../docs/DEPLOYMENT.md) and
[Development Guide](../docs/DEVELOPMENT.md).

## Future contents

- Terraform / Pulumi modules
- Kubernetes or ECS definitions
- Environment overlays (staging, production)
- Observability stack configuration

## Assumptions

- Local development uses Docker Compose only
- Production topology will expand [Architecture Summary](../docs/ARCHITECTURE_SUMMARY.md)
  and [ARCHITECTURE.md](../docs/ARCHITECTURE.md) when defined
- Secrets are never committed

## Related documents

- [Documentation index](../docs/README.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)
- [Tech Stack](../docs/TECH_STACK.md)
- [Root README](../README.md)
