# Documentation Rules

## Documentation as part of delivery

- Documentation changes ship with the code or process they describe.
- Use one authoritative source and link to it; do not duplicate instructions that
  will drift.
- Write for a new engineer with repository access but no tribal knowledge.
- Commands must be copyable, scoped to the correct directory, and safe by default.
- Distinguish current behavior, planned behavior, examples, and unresolved TODOs.

## Document ownership

- `README.md`: project purpose, repository map, and fastest supported start.
- `docs/DEVELOPMENT.md`: complete local setup and daily workflow.
- `docs/ARCHITECTURE.md`: current system structure, boundaries, and runtime flows.
- `docs/adr/`: immutable architectural decisions and their trade-offs.
- `docs/PRD.md`: product outcomes and scope, not implementation details.
- `specs/`: approved feature behavior, contracts, non-functional requirements, and
  acceptance criteria before implementation.
- `docs/ROADMAP.md`: directional sequencing, not a commitment tracker.
- `agents/` and `.cursor/rules/`: AI agent authority, boundaries, and governance.

## Architecture decision records

- Add an ADR for durable, cross-cutting, difficult-to-reverse, or dependency-shaping
  decisions.
- Use the next zero-padded number and a lowercase kebab-case filename.
- Required sections: Status, Context, Decision, Alternatives considered, and
  Consequences.
- Accepted ADRs are not rewritten to hide history. Supersede them with a new ADR and
  link both records.
- Keep `docs/DECISIONS.md` as the index and update it in the same pull request.

## Specifications and APIs

- A feature spec states goals, non-goals, behavior, ownership, data classification,
  API/events, failure modes, observability, rollout, testing, and open questions.
- OpenAPI models and endpoint descriptions are part of the public contract.
- Document compatibility and migration for breaking API, schema, prompt, model, or
  configuration changes.
- Examples use synthetic data and must not contain secrets or personal information.

## Code documentation

- Public modules and interfaces explain purpose, invariants, side effects, errors,
  and lifecycle requirements when these are not obvious from types.
- Comments explain why a constraint exists. Do not narrate straightforward code.
- TODO/FIXME entries include an issue or owner and an actionable removal condition.

## Review checklist

- Names, paths, ports, commands, and supported versions match the repository.
- Links resolve and headings are scannable.
- Security-sensitive examples are safe and use placeholders.
- The architectural impact and operational behavior are documented.
- No future capability is represented as already implemented.
