# Documentation index

> **Version:** 1 (RC1.5 documentation polish)  
> **Rule:** Prefer this index and short guide pages; open feature specs and ADRs for detail—do not copy them here.

Every major Version 1 document is reachable in **one click** from this page, and in
**at most two clicks** from the [repository root README](../README.md).

## Start here

| Guide | Purpose |
| --- | --- |
| [Project Overview](OVERVIEW.md) | What RAG-enterprise is, who it is for, and V1 scope |
| [Quick Start](../README.md#quick-start) | Fastest local path (also expanded below via Development) |
| [Development Guide](DEVELOPMENT.md) | Prerequisites, Compose, backend/frontend setup, quality gates |
| [Development Workflow](DEVELOPMENT_WORKFLOW.md) | Day-to-day contribution process |
| [Contributing](CONTRIBUTING.md) | PR checklist and package entry points |

## Product and architecture

| Guide | Purpose |
| --- | --- |
| [Architecture Summary](ARCHITECTURE_SUMMARY.md) | V1 system picture + ADR map (links only) |
| [Architecture notes](ARCHITECTURE.md) | Evolving runtime notes (backend lifecycle, health) |
| [Feature Map](FEATURE_MAP.md) | Specs 001–008 and backend module docs |
| [Product Requirements](PRD.md) | Product skeleton (not a living feature inventory) |
| [Tech Stack](TECH_STACK.md) | Adopted and planned technologies |
| [Roadmap](ROADMAP.md) | Directional sequencing |
| [ADR index](DECISIONS.md) | Architecture Decision Records |

## Operate and evaluate

| Guide | Purpose |
| --- | --- |
| [Deployment Guide](DEPLOYMENT.md) | Local Compose today; production deferred |
| [Evaluation Guide](EVALUATION_GUIDE.md) | Feature 007 offline evaluation |
| [Demo Guide](DEMO_GUIDE.md) | Official Persian demo workspace (RC1.4) |
| [E2E Happy Path (RC1.3)](backend/E2E_HAPPY_PATH.md) | Single automated golden-path test |

## Backend deep links

| Document | Topic |
| --- | --- |
| [API Foundation](backend/API_FOUNDATION.md) | Envelopes, versioning, OpenAPI |
| [Configuration (RC1.1)](backend/CONFIGURATION.md) | Startup validation |
| [Local File Storage (RC1.6)](backend/LOCAL_FILE_STORAGE.md) | Durable upload binaries on disk |
| [Process & Index (RC1.6)](backend/PROCESS_AND_INDEX.md) | Synchronous uploaded → indexed action |
| [Operational Health (RC1.2)](backend/OPERATIONAL_HEALTH.md) | `/live`, `/ready`, `/system` |
| [Persistence](backend/PERSISTENCE_LAYER.md) | Database session and models |
| [Application layer](backend/APPLICATION_LAYER.md) | Commands, queries, results |
| [Knowledge management](backend/KNOWLEDGE_MANAGEMENT.md) | KB, documents, uploads |
| [Embeddings & retrieval](backend/EMBEDDINGS_AND_RETRIEVAL.md) | Indexing and dense search |
| [RAG generation](backend/RAG_GENERATION.md) | Chat, citations, abstention |
| [Evaluation framework](backend/EVALUATION_FRAMEWORK.md) | Offline experiments |

## Domain and data

| Area | Entry |
| --- | --- |
| Domain | [Domain model](domain/DOMAIN_MODEL.md) · [Bounded contexts](domain/BOUNDED_CONTEXTS.md) · [Glossary](domain/DOMAIN_GLOSSARY.md) |
| Data | [Data architecture](data/DATA_ARCHITECTURE.md) · [Lifecycle](data/DATA_LIFECYCLE.md) · [Storage](data/STORAGE_STRATEGY.md) |

## Package READMEs

| Package | README |
| --- | --- |
| Backend | [backend/README.md](../backend/README.md) |
| Frontend | [frontend/README.md](../frontend/README.md) |
| Specs | [specs/README.md](../specs/README.md) |
| Demo | [demo/README.md](../demo/README.md) |
| Infrastructure | [infrastructure/README.md](../infrastructure/README.md) |
| Cross-cutting tests | [tests/README.md](../tests/README.md) |

## Consistent guide layout

Version 1 guide pages use this section order where applicable:

1. Purpose
2. Audience
3. Steps or map (links, not copies)
4. Related documents

## Link health

From the repository root:

```bash
uv run python scripts/verify-doc-links.py
npx --yes markdownlint-cli2
```

Config: [`.markdownlint-cli2.jsonc`](../.markdownlint-cli2.jsonc).

## Related

- [AI / governance rules](../.cursor/rules/)
- [Agent roles](../agents/)
