# Python Rules

## Runtime and tooling

- Python is managed only from `backend/` with `uv`; the virtual environment is
  `backend/.venv`. Never create a repository-root environment.
- Source lives under `backend/src/rag_enterprise/`; tests live under
  `backend/tests/` and mirror source package boundaries.
- `uv.lock` is committed. Add or remove packages with `uv`, never by editing the
  lockfile or using `pip` directly.
- Required gates: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy src`, and `uv run pytest`.

## Types and models

- All production functions, methods, fields, and module-level collections are
  explicitly typed and pass strict MyPy.
- Use Pydantic models at external boundaries and domain dataclasses/value objects
  internally. Do not use untyped dictionaries as service contracts.
- Prefer protocols or narrow abstract interfaces for injected dependencies.
- Avoid `Any`, casts, and type ignores. A necessary suppression must be narrow,
  include the error code, and explain the incompatible dependency.
- Use UTC-aware datetimes and explicit units for durations and sizes.

## FastAPI

- Routers only parse/validate requests, invoke injected application services, and
  map results. No business logic, ORM queries, or provider SDK calls in routes.
- Every public endpoint has explicit request and response models, status codes,
  error behavior, and API versioning under `/api/v1`.
- Provide dependencies through `Depends` at composition boundaries. Services use
  constructor injection and must not call the global container.
- Settings are injected from `core/config`; do not read `os.environ` elsewhere.
- Initialize database pools, Redis, HTTP clients, and provider clients in lifespan
  and close them deterministically.

## Async and persistence

- Use async APIs for I/O paths. Do not call blocking file, network, SDK, or database
  operations on the event loop.
- Await every coroutine; bound concurrency and queues; make cancellation safe.
- Every outbound call has a timeout. Retries follow project error-handling rules.
- SQLAlchemy 2 code must use async sessions, explicit transactions, and repository
  interfaces. Never share sessions across requests or tasks.
- Avoid lazy loading and hidden N+1 queries; state loading strategy explicitly.

## Errors, logging, and modules

- Raise domain/application errors independent of HTTP. Translate to HTTP errors in
  the API layer and preserve exception causes.
- Use the configured structured logger; never use `print`.
- Keep module imports side-effect free. No client creation, settings mutation, or
  network access at import time.
- Use absolute imports from `rag_enterprise`; avoid circular imports and wildcard
  exports.

## Tests

- Async behavior uses `pytest-asyncio`; HTTP tests use `httpx.AsyncClient`.
- Override injected dependencies in tests; never call real cloud/LLM services.
- Test transaction boundaries, timeout/error translation, and cleanup for resource
  adapters.
