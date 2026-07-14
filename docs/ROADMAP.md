# Roadmap

> **Status:** Directional sequencing — not a commitment tracker.  
> **Release:** Version 1.0.0 shipped.  
> **Living capability map:** [Feature Map](FEATURE_MAP.md)

## Version 1.0.0 (complete)

Shipped capabilities (see [Feature Map](FEATURE_MAP.md) for links):

- [x] Monorepo, FastAPI backend, React operator console
- [x] Local Docker Compose (PostgreSQL + pgvector, Redis)
- [x] SQLAlchemy 2 persistence and Alembic migrations
- [x] Knowledge management (create, publish, archive, restore)
- [x] Document upload with **local filesystem storage**
- [x] Document processing, chunking, embeddings, dense retrieval
- [x] Synchronous **Process & Index** operator action
- [x] Grounded chat with citations and abstention
- [x] Offline evaluation engine + evaluation dashboard (read adapters)
- [x] Health endpoints (`/live`, `/ready`, `/system`)
- [x] Official Persian demo corpus and CI golden-path E2E
- [x] Configuration validation and Version 1.0.0 release metadata

## Version 2 (planned)

Future work only — not implemented in Version 1.0.0:

- Authentication and real identity (replace development actor headers)
- Background workers / async job queues
- Streaming responses (chat / SSE / websockets)
- Agent tools and LangGraph orchestration
- Experiment authoring UI (beyond offline runner + dashboard reads)
- Provider administration UI and multi-provider ops
- Multi-node / production deployment topology
- Hybrid search, distributed tracing, and expanded observability

## Related documents

- [Feature Map](FEATURE_MAP.md)
- [Project Overview](OVERVIEW.md)
- [Release Notes](../RELEASE_NOTES.md)
- [Changelog](../CHANGELOG.md)
- [Documentation index](README.md)
