## Summary

<!-- What changed, why is it needed, and what is explicitly out of scope? -->

- 

Related issue/specification:

## Testing performed

<!-- List exact commands and relevant manual scenarios. Do not mark unrun checks. -->

- [ ] Backend lint: `cd backend && uv run ruff check .`
- [ ] Backend format: `cd backend && uv run ruff format --check .`
- [ ] Backend types: `cd backend && uv run mypy src`
- [ ] Backend tests: `cd backend && uv run pytest`
- [ ] Frontend lint: `cd frontend && npm run lint`
- [ ] Frontend format: `cd frontend && npm run format:check`
- [ ] Frontend tests: `cd frontend && npm run test`
- [ ] Frontend build: `cd frontend && npm run build`
- [ ] Not applicable (explain below)

Evidence or additional test notes:

## Architectural impact

<!-- Describe boundary, dependency, API, schema, configuration, infrastructure,
AI/model/prompt, observability, migration, rollout, and rollback impact. Write "None"
with a reason if there is no architectural impact. Link ADRs where applicable. -->

- [ ] Existing architecture and ADRs are followed
- [ ] New or superseding ADR added (if required)
- [ ] Backward compatibility and migration are addressed
- [ ] Rollout and rollback are documented

Details:

## Security and data impact

<!-- Note changes to trust boundaries, authorization, tenancy, secrets, PII,
documents, embeddings, logs, retention, dependencies, or external providers. -->

- [ ] No secrets or sensitive production data are included
- [ ] Inputs, errors, logs, and telemetry were reviewed
- [ ] Security review requested where required

Details:

## Screenshots or recordings

<!-- Required for UI changes. Include before/after and relevant responsive,
loading, empty, error, success, and dark-mode states. Write "Not applicable" for
non-UI changes. Do not include sensitive data. -->

## Reviewer notes

<!-- Call out high-risk areas, deliberate trade-offs, follow-up work, and suggested
review order. -->

## Final checklist

- [ ] Change is limited to one coherent outcome
- [ ] Tests cover new behavior and regressions
- [ ] Documentation and specifications are updated
- [ ] Lockfiles changed only through their package managers
- [ ] No unrelated generated artifacts are included
- [ ] I reviewed the complete diff
