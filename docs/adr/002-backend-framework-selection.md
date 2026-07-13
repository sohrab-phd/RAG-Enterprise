# ADR-002: Backend Framework Selection

**Status:** Accepted  
**Date:** 2026-07-13

## Context

RAG-enterprise needs an async-first, typed HTTP API with OpenAPI contracts, explicit
dependency injection, deterministic resource lifecycle, and strong Python tooling.
Future work is expected to integrate PostgreSQL, Redis, document processing, and
model providers, but business logic must remain portable and testable outside the
web framework.

## Decision

Use Python 3.12+, FastAPI, Pydantic, pydantic-settings, Uvicorn, and structlog.
Manage the backend with `uv`, a committed `uv.lock`, a `src` layout, and
`backend/.venv`. Use:

- an application factory and FastAPI lifespan for resource lifecycle;
- API versioning under `/api/v1`;
- FastAPI `Depends` only at delivery/composition boundaries;
- constructor injection and domain-owned interfaces within application code;
- async I/O adapters and explicit timeouts;
- Ruff, strict MyPy, pytest, pytest-asyncio, and HTTPX as quality gates.

FastAPI request/response models and provider SDK types must not become domain models.

## Alternatives considered

### Django and Django REST Framework

Mature and batteries-included, especially for ORM/admin workflows, but introduces a
larger framework surface and conventions that do not align as directly with the
platform's async API-first and explicit-adapter goals.

### Flask

Simple and flexible, but requires more choices and integration work for async,
validation, OpenAPI, dependency wiring, and consistent enterprise conventions.

### Node.js backend

Would align language with the frontend, but Python provides the strongest ecosystem
fit for the planned data, ML, LangGraph, and evaluation workloads.

## Consequences

- Typed validation and OpenAPI documentation are available from the foundation.
- Async external operations can be handled efficiently, but blocking SDKs must be
  isolated or offloaded.
- FastAPI dependency mechanisms must be prevented from spreading into domain code.
- Pydantic model changes can affect API contracts and require compatibility review.
- The team owns application layering; FastAPI does not enforce clean architecture.
- Python and dependency versions are reproducible through `uv` and the lockfile.
