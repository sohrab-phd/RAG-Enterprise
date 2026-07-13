# Contributing

> **Status:** Draft skeleton — TODO: expand as team processes mature.

## Getting Started

1. Clone the repository
2. Copy `.env.example` to `.env`
3. Start infrastructure: `docker compose up -d`
4. Set up backend: see [backend/README.md](../backend/README.md)
5. Set up frontend: see [frontend/README.md](../frontend/README.md)

## Development Workflow

<!-- TODO: Branch naming, PR process, review requirements -->

## Code Quality

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

## Commit Guidelines

<!-- TODO: Conventional commits or team standard -->

## Pull Request Checklist

- [ ] Tests pass locally
- [ ] Lint/format checks pass
- [ ] Documentation updated (if applicable)
- [ ] No secrets committed
- [ ] TODO: Add security review criteria for sensitive changes

## AI-Assisted Development

See [agents/](../agents/) for specialized agent roles and [.cursor/rules/](../.cursor/rules/) for IDE guidance.
