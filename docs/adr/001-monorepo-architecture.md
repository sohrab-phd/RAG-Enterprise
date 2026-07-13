# ADR-001: Monorepo Architecture

**Status:** Accepted  
**Date:** 2026-07-13

## Context

RAG-enterprise will evolve across a Python API, React application, data services,
AI workflows, infrastructure, specifications, and shared engineering governance.
Many changes will alter contracts across these areas and must be reviewed and tested
as one coherent unit. The platform is still establishing domain boundaries, and
prematurely independent repositories would add release coordination and duplicated
tooling before independent deployment or ownership is justified.

## Decision

Use one Git monorepo with explicit top-level ownership boundaries:

- `backend/` is the independently managed Python package and runtime.
- `frontend/` is the independently managed Node/TypeScript package and runtime.
- `infrastructure/`, `docs/`, `specs/`, `scripts/`, `tests/`, `agents/`, and
  `.cursor/rules/` contain their named cross-cutting concerns.
- Each runtime owns its dependency manifest, lockfile, build, and tests.
- Source code is not imported across runtime boundaries; integration uses versioned
  contracts.
- Begin as a modular monolith. Extract independently deployed services only through
  a later ADR supported by scaling, reliability, or organizational evidence.

## Alternatives considered

### Separate repositories by runtime

Provides strong ownership and release isolation, but creates cross-repository contract
coordination, duplicated governance, and version skew before teams require that autonomy.

### Python or JavaScript workspace tooling at the repository root

Could centralize commands, but would blur runtime ownership and conflict with the
requirement that Python's environment remain in `backend/.venv`.

### Microservices from inception

Offers independent deployment but adds network failure modes, distributed tracing,
schema coordination, operational cost, and local-development complexity without
validated service boundaries.

## Consequences

- Cross-cutting changes, ADRs, specifications, and CI can be reviewed atomically.
- Backend and frontend retain independent toolchains and lockfiles.
- CI must use path-aware or parallel jobs as the repository grows.
- Code ownership and dependency direction must be actively enforced to prevent a
  tightly coupled monolith.
- Repository size and checkout time may grow; this will be measured before adopting
  partial checkout or repository extraction.
