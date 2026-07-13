# Coding Standards

## Change discipline

- Implement the smallest complete change that satisfies an approved specification.
- Keep functions and components cohesive, explicit, and easy to test. Extract code
  because responsibilities differ, not merely to reduce line count.
- Prefer established project patterns over introducing abstractions or dependencies.
- Remove dead code; do not leave commented-out implementations or speculative hooks.
- Do not perform unrelated refactors in feature or defect pull requests.

## Naming and interfaces

- Use domain language from `docs/PRD.md` and feature specifications consistently.
- Names describe intent and units: `timeout_seconds`, `document_id`, `is_ready`.
- Avoid vague names such as `data`, `manager`, `processor`, and `helper` unless the
  scope makes the meaning unambiguous.
- Boolean names begin with `is`, `has`, `can`, or `should`.
- Public interfaces are narrow, typed, and documented. Prefer immutable inputs and
  return values over mutating arguments.
- Do not expose persistence records or provider SDK objects across layer boundaries.

## Error handling

- Fail explicitly. Never swallow exceptions or use a broad catch without re-raising,
  translating, or recording an intentional fallback.
- Define errors at the layer that owns their meaning. Preserve the original cause.
- User-facing errors must be stable, actionable, and free of internal details.
- Retries are allowed only for transient, idempotent operations; they must be
  bounded, use backoff and jitter, and emit metrics.
- Do not use exceptions for expected control flow.

## Logging and observability

- Use structured logging with stable event names and fields; do not build messages
  through string interpolation.
- Log once at the boundary that handles an error. Avoid duplicate stack traces.
- Include correlation IDs and safe resource identifiers where available.
- Never log secrets, credentials, tokens, raw prompts, document contents, personal
  data, or full request/response bodies.
- Add metrics or traces for material latency, reliability, and AI cost paths.

## Comments and dependencies

- Comments explain decisions, invariants, and non-obvious trade-offs—not syntax.
- TODOs include an issue/reference and the condition for removal; avoid anonymous
  TODOs in production paths.
- Add dependencies only when existing libraries or standard APIs are insufficient.
  Document ownership, license, maintenance health, security posture, and bundle or
  runtime impact in the pull request.

## Completion gate

- Format, lint, type-check, and relevant tests pass locally.
- Tests cover success, boundary, and failure behavior.
- Documentation and contracts are updated with the implementation.
- No warnings are introduced or suppressed without a documented reason.
