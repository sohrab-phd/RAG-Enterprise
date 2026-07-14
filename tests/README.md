# Cross-Cutting Integration Tests

> **Status:** Placeholder for future multi-package suites.

## Purpose

Reserved for integration tests that span packages (for example backend + Compose
Postgres + Redis). Package tests stay next to their code today.

## Current state

| Layer | Location |
| --- | --- |
| Backend unit / API / E2E golden path | `backend/tests/` ([E2E Happy Path](../docs/backend/E2E_HAPPY_PATH.md)) |
| Frontend component tests | `frontend` Vitest suites |

## Future work

- Compose test profile
- Cross-service API contract tests
- Post-deploy smoke tests in CI

## Related documents

- [Documentation index](../docs/README.md)
- [Development Guide](../docs/DEVELOPMENT.md)
- [Root README](../README.md)
