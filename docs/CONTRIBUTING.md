# Contributing

> **Purpose:** How to contribute to RAG-enterprise Version 1.

## Purpose

Get a working local environment and land changes that match package boundaries,
specs, and quality gates.

## Getting started

1. Clone the repository.
2. Follow [Quick Start](../README.md#quick-start) or the full
   [Development Guide](DEVELOPMENT.md).
3. Read [Project Overview](OVERVIEW.md) and [Architecture Summary](ARCHITECTURE_SUMMARY.md).
4. Package entry points: [backend/README.md](../backend/README.md),
   [frontend/README.md](../frontend/README.md).

## Development workflow

See [Development Workflow](DEVELOPMENT_WORKFLOW.md) for branch → PR steps.

## Code quality

### Backend

```bash
cd backend
uv run ruff check .
uv run ruff format .
uv run mypy src
uv run pytest
```

### Frontend

```bash
cd frontend
npm run lint
npm run format:check
npm run test
npm run build
```

## Pull request checklist

- [ ] Tests pass locally
- [ ] Lint / format / type checks pass
- [ ] Documentation or OpenAPI updated when behavior changes
- [ ] No secrets committed
- [ ] Spec / ADR consulted for behavioral or architectural changes

## AI-assisted development

See [agents/](../agents/) and [.cursor/rules/](../.cursor/rules/).

## Related documents

- [Documentation index](README.md)
- [Feature Map](FEATURE_MAP.md)
- [ADR index](DECISIONS.md)
- [Root README](../README.md)
