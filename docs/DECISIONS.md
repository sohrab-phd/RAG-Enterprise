# Architecture Decision Records

Architecture Decision Records (ADRs) capture durable, cross-cutting, or
difficult-to-reverse technical decisions for RAG-enterprise. Detailed records live
in [`docs/adr/`](adr/).

**Navigation:** [Architecture Summary](ARCHITECTURE_SUMMARY.md) ·
[Documentation index](README.md)

## Decision index

| ADR | Decision | Status |
| --- | --- | --- |
| [001](adr/001-monorepo-architecture.md) | Monorepo Architecture | Accepted |
| [002](adr/002-backend-framework-selection.md) | Backend Framework Selection | Accepted |
| [003](adr/003-database-selection.md) | Database Selection | Accepted |
| [004](adr/004-frontend-selection.md) | Frontend Selection | Accepted |
| [005](adr/005-ai-platform-principles.md) | AI Platform Principles | Accepted |

## Lifecycle

1. Use the next zero-padded sequence number and a lowercase kebab-case filename.
2. Include Status, Date, Context, Decision, Alternatives considered, and Consequences.
3. Open new records as **Proposed** and obtain relevant architecture, security, data,
   infrastructure, and AI reviews.
4. Change the status to **Accepted** when approved.
5. Do not rewrite accepted history to conceal a changed decision. Add a new ADR,
   mark the old record **Superseded**, and link the records in both directions.
6. Use **Deprecated** when a decision is no longer recommended but has not been
   superseded by a single replacement.

## When an ADR is required

- A new framework, datastore, protocol, deployment unit, or major dependency.
- A change to module boundaries, dependency direction, ownership, or data authority.
- A security, tenancy, compliance, or retention model decision.
- A public API, event, schema, model, prompt, embedding, or index versioning strategy.
- A choice with material migration, operational, scalability, cost, or lock-in impact.

Routine implementation details that follow existing ADRs belong in feature
specifications or code review, not in a new ADR.
