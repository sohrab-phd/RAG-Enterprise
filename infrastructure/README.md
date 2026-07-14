# Infrastructure

> **Release:** 1.0.0  
> **Status:** Local Docker Compose supported; production deployment deferred.

Compose services at the repository root carry OCI / project labels
`com.rag-enterprise.version=1.0.0` (metadata only; no app images yet).

## Purpose

Document today’s local dependency stack and hold IaC for **Version 2** multi-node
deployment. Runtime Compose file lives at the **repository root**
(`docker-compose.yml`), not under this folder yet.

## Local development

| Service | Image | Purpose |
| --- | --- | --- |
| postgres | `pgvector/pgvector:pg16` | PostgreSQL with pgvector |
| redis | `redis:7-alpine` | Local Compose service (not required for core V1 RAG path) |

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
