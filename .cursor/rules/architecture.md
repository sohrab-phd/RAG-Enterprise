# Architecture Rules

## Scope and authority

These rules apply to every change in RAG-enterprise. Approved ADRs in `docs/adr/`
record exceptions and supersede this file where they conflict.

## System boundaries

- Preserve the top-level boundaries: `backend/`, `frontend/`, `infrastructure/`,
  `docs/`, `specs/`, `scripts/`, and `tests/`.
- Do not import source code across package boundaries. Integrate through explicit,
  versioned contracts.
- A change spanning two or more boundaries must document ownership, contracts,
  failure behavior, and rollout impact in its specification or ADR.
- Keep domain logic independent of FastAPI, React, SQLAlchemy, Redis, model SDKs,
  and other delivery or infrastructure frameworks.

## Backend dependency direction

- Dependencies flow inward: API routes -> application services -> domain
  interfaces; infrastructure adapters implement domain-owned interfaces.
- API routes validate and translate HTTP data, invoke one application use case,
  and map results to response models. They contain no business rules or queries.
- Use constructor or FastAPI dependency injection. Never instantiate repositories,
  clients, settings, or model providers inside business functions.
- Keep configuration in the settings package. Environment access outside settings
  and startup wiring is forbidden.
- External resources are initialized and closed through application lifespan.
- Cross-layer circular imports and service-locator access from domain code are
  forbidden.

## Frontend dependency direction

- Organize feature code by business capability; keep reusable primitives in
  `components/ui` and framework-neutral helpers in `lib`.
- UI components depend on typed feature interfaces, not transport response shapes.
- Centralize API transport, authentication headers, error translation, and
  cancellation. Components must not scatter raw `fetch` calls.
- Separate server state, local interaction state, and URL state. Do not mirror
  server data into global client state without a documented need.

## Cross-cutting requirements

- Every external operation has an explicit timeout, bounded retry policy where
  safe, structured logs, and a defined failure result.
- Propagate correlation identifiers across HTTP, background work, database access,
  and AI calls. Never log prompts, documents, credentials, or PII by default.
- Design writes for idempotency where retries are possible.
- Public interfaces use stable types and are changed compatibly or versioned.
- New architectural patterns require an ADR before broad adoption.

## Prohibited patterns

- Business logic in routes, React components, ORM models, migrations, or scripts.
- Global mutable state, hidden singletons, import-time network calls, or unbounded
  background tasks.
- Direct infrastructure dependencies in domain code.
- Generic `utils`, `helpers`, or `common` dumping grounds without cohesive purpose.
- Premature distributed services; begin as a modular monolith unless an ADR
  demonstrates an independently deployable boundary.
