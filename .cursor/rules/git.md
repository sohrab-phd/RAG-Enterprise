# Git Rules

## Branching

- `main` is protected, releasable, and never receives direct feature commits.
- Create short-lived branches from current `main`: `feat/<scope>`, `fix/<scope>`,
  `docs/<scope>`, `chore/<scope>`, or `refactor/<scope>`.
- Keep branches focused on one coherent outcome and rebase or merge current `main`
  before final review according to repository policy.
- Do not rewrite shared branch history or force-push `main`.

## Commits

- Each commit is buildable, reviewable, and contains no unrelated generated files.
- Use imperative Conventional Commit subjects:
  `type(scope): concise outcome`.
- Allowed types include `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`,
  `perf`, and `security`.
- Use the body to explain motivation, trade-offs, migration, and issue references.
- Never bypass hooks or checks without explicit human approval and documented reason.

## Pull requests

- Open a PR only after self-review and local relevant checks pass.
- Complete `.github/PULL_REQUEST_TEMPLATE.md`; state scope, tests, architecture,
  security/data impact, rollout, and screenshots for UI changes.
- Prefer fewer than 400 changed production lines. Split independent or high-risk
  concerns; generated lockfiles and migrations are excluded from this guideline.
- Keep API, schema, behavior, docs, and tests in one atomic PR when they form one
  change.
- Resolve review comments with code or a reasoned response. Do not silently dismiss
  unresolved architectural or security concerns.

## Review and merge

- At least one qualified human reviewer approves every PR.
- Architecture, database, security, infrastructure, and AI changes require the
  corresponding owner/agent review in addition to normal code review.
- All required CI checks must pass and review conversations must be resolved.
- Use squash merge by default to keep `main` concise; the squash message follows
  Conventional Commits.
- Delete merged branches. Reverts use a dedicated PR and explain user/operational
  impact.

## Protected content

- Never commit `.env`, credentials, private keys, tokens, production exports,
  customer documents, model-provider payloads, or PII.
- Inspect staged changes before every commit. If a secret may have been committed,
  stop and rotate/revoke it before history remediation.
- Do not commit `backend/.venv`, `node_modules`, build output, logs, coverage, IDE
  state, or large binaries unless explicitly governed.
- Lockfiles are committed and changed only through their package managers.

## AI-assisted changes

- The human author remains accountable for generated code and documentation.
- PRs disclose material AI-generated changes when required by organizational policy.
- Never paste proprietary code, secrets, or sensitive data into unapproved models.
