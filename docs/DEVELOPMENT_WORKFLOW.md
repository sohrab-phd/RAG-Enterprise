# Development Workflow

> **Purpose:** Day-to-day contribution process for Version 1.  
> **Detail:** Commands and environment setup live in [DEVELOPMENT.md](DEVELOPMENT.md).

## Purpose

Describe how changes move from branch to merge without repeating setup instructions.

## Audience

Engineers and AI-assisted contributors working inside package boundaries.

## Workflow

1. Sync `main` and create a short-lived branch (`feat/…`, `fix/…`, `docs/…`, `chore/…`).
2. Read the relevant **spec**, **ADR**, and `.cursor/rules` before coding.
3. Prefer the smallest coherent change; no unrelated refactors.
4. Add or update tests with the behavior change.
5. Update docs or OpenAPI contracts in the same change when behavior is user-visible.
6. Run package quality gates ([DEVELOPMENT.md](DEVELOPMENT.md#testing-and-quality-commands)).
7. Commit with Conventional Commits; open a PR using the repository template.
8. Keep CI green; request specialist review for architecture, data, security, infra, or AI changes.

Expanded narrative: [DEVELOPMENT.md — Development workflow](DEVELOPMENT.md#development-workflow).

## Package commands (pointers)

| Package | README |
| --- | --- |
| Backend | [backend/README.md](../backend/README.md) |
| Frontend | [frontend/README.md](../frontend/README.md) |

## Pull requests

Checklist and getting-started: [CONTRIBUTING.md](CONTRIBUTING.md).

## Governance

- Specs: [specs/README.md](../specs/README.md)
- ADRs: [DECISIONS.md](DECISIONS.md)
- Agents / rules: [agents/](../agents/), [.cursor/rules/](../.cursor/rules/)

## Related documents

- [Development Guide](DEVELOPMENT.md)
- [Feature Map](FEATURE_MAP.md)
- [Documentation index](README.md)
