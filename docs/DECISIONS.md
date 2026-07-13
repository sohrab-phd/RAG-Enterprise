# Architecture Decision Records (ADR)

> **Status:** Draft skeleton — TODO: add ADRs as decisions are made.

## Format

Each decision should follow this template:

1. **Title** — Short descriptive name
2. **Status** — Proposed | Accepted | Deprecated | Superseded
3. **Context** — What problem are we solving?
4. **Decision** — What did we decide?
5. **Consequences** — Trade-offs and follow-up work

---

## ADR-001: Monorepo Structure

**Status:** Accepted

**Context:** RAG-enterprise requires coordinated backend, frontend, and infrastructure development.

**Decision:** Use a single monorepo with clear top-level boundaries (`backend/`, `frontend/`, `infrastructure/`).

**Consequences:** Simplifies local development and cross-cutting changes; requires disciplined CI and ownership boundaries.

---

## ADR-002: uv for Python Dependency Management

**Status:** Accepted

**Context:** Need reproducible, fast Python environments for enterprise development.

**Decision:** Use `uv` with `backend/.venv` (not a root virtual environment) and src layout.

**Consequences:** Developers must use `uv` commands in `backend/`; CI must mirror this setup.

---

## ADR-003: API Versioning

**Status:** Accepted

**Context:** Enterprise APIs require stable contracts and migration paths.

**Decision:** Version APIs under `/api/v1` from the start.

**Consequences:** Breaking changes require new version namespaces.

---

## Future ADRs

<!-- TODO: ADR-004 Database access pattern (SQLAlchemy 2 async) -->
<!-- TODO: ADR-005 Authentication strategy -->
<!-- TODO: ADR-006 RAG pipeline architecture -->
<!-- TODO: ADR-007 Deployment platform -->
