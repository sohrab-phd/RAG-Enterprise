# Testing Rules

## Policy

- Every behavior change includes automated tests in the same pull request.
- Test observable contracts and invariants, not private implementation details.
- Cover the happy path, relevant boundaries, validation failures, dependency
  failures, timeouts, and authorization decisions where applicable.
- A defect fix begins with a regression test that fails for the reported behavior.
- Tests must be deterministic, isolated, order-independent, parallel-safe, and
  free of real internet or model-provider calls.

## Test layers

- Unit tests exercise domain and application logic without framework or network I/O.
- Component/adapter tests exercise API routes, repositories, provider adapters, and
  React components against controlled dependencies.
- Integration tests validate PostgreSQL, pgvector, Redis, and cross-boundary
  contracts using disposable services.
- End-to-end tests are reserved for a small set of critical user journeys after
  those journeys exist.
- Do not replace lower-layer tests with broad end-to-end tests.

## Backend

- Use pytest, pytest-asyncio, and `httpx.AsyncClient`; mirror source paths under
  `backend/tests/`.
- Inject fakes or stubs through defined interfaces. Avoid patching internals when a
  dependency boundary exists.
- Database tests use isolated transactions or disposable databases and verify
  commit, rollback, constraints, and concurrency behavior.
- Freeze time and random inputs when they affect assertions.
- Assert structured error contracts and status codes, not incidental exception text.

## Frontend

- Use Vitest and Testing Library; test through accessible roles, labels, and visible
  outcomes.
- Cover loading, empty, failure, retry, and success states for data-driven UI.
- Mock the network boundary, not React internals or child components by default.
- Use snapshots only for small stable serialized outputs; snapshots do not replace
  behavioral assertions.
- Accessibility-critical components require keyboard and accessible-name assertions.

## AI systems

- Maintain versioned evaluation datasets for retrieval relevance, groundedness,
  citation fidelity, safety, latency, and cost.
- Separate deterministic unit tests from provider-dependent evaluation runs.
- Pin model and prompt configuration in evaluation results and define acceptance
  thresholds before changing a production AI path.
- Never use production documents, secrets, or uncontrolled PII in test fixtures.

## Coverage and CI

- New or changed production code requires meaningful branch coverage; 80% coverage
  is the repository baseline once coverage enforcement is enabled.
- Security-, authorization-, data-integrity-, and billing-critical logic targets
  complete branch coverage.
- Coverage percentage cannot justify weak assertions or tests of generated code.
- CI must pass lint, format, types, tests, and build. Flaky tests are defects: fix or
  quarantine with an owner, issue, and expiry date; never add blind retries.
