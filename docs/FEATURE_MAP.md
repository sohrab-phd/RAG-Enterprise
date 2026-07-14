# Feature Map

> **Purpose:** Navigate Version 1.0.0 capabilities without opening every folder.  
> **Release:** 1.0.0  
> **Authority:** Behavior details live in `specs/` and backend module docs—this page only maps them.

## Purpose

Show which features exist in Version 1.0.0, their specification entry points, and the
backend documentation that describes the shipped implementation notes.

## Version 1.0.0 — Implemented

| Spec / topic | Capability | Status | Spec entry | Implementation notes |
| --- | --- | --- | --- | --- |
| 001 | Knowledge bases, folders, documents, uploads, versions, **Publish** | **Implemented** | [README](../specs/001-knowledge-management/README.md) | [KNOWLEDGE_MANAGEMENT.md](backend/KNOWLEDGE_MANAGEMENT.md) |
| 002 | Document text extraction / Persian normalization | **Implemented** | [SPEC](../specs/002-document-processing/SPEC.md) | Used by Process & Index |
| 003 | Chunk generation | **Implemented** | [SPEC](../specs/003-chunking/SPEC.md) | `ChunkingService` via Process & Index |
| 004 | Dense embeddings (pgvector path) | **Implemented** | [SPEC](../specs/004-embeddings/SPEC.md) | [EMBEDDINGS_AND_RETRIEVAL.md](backend/EMBEDDINGS_AND_RETRIEVAL.md) |
| 005 | Dense vector retrieval | **Implemented** | [SPEC](../specs/005-retrieval/SPEC.md) | same as above |
| 006 | Grounded generation, citations, abstention | **Implemented** | [SPEC](../specs/006-rag-generation/SPEC.md) | [RAG_GENERATION.md](backend/RAG_GENERATION.md) |
| 007 | Offline golden-dataset evaluation | **Implemented** | [README](../specs/007-evaluation-framework/README.md) | [EVALUATION_FRAMEWORK.md](backend/EVALUATION_FRAMEWORK.md) |
| 008 | Operator console (Knowledge, Chat, Evaluation) | **Implemented** | [README](../specs/008-frontend/README.md) | [frontend/README.md](../frontend/README.md) |
| RC1.1 | Configuration validation | **Implemented** | — | [CONFIGURATION.md](backend/CONFIGURATION.md) |
| RC1.2 | `/live`, `/ready`, `/system` | **Implemented** | — | [OPERATIONAL_HEALTH.md](backend/OPERATIONAL_HEALTH.md) |
| RC1.3 | End-to-end happy path test | **Implemented** | — | [E2E_HAPPY_PATH.md](backend/E2E_HAPPY_PATH.md) |
| RC1.4 | Official demo workspace | **Implemented** | — | [Demo Guide](DEMO_GUIDE.md) · [demo/](../demo/README.md) |
| RC1.5 | Documentation polish | **Implemented** | — | [Documentation index](README.md) |
| RC1.6 | Local filesystem upload storage | **Implemented** | — | [LOCAL_FILE_STORAGE.md](backend/LOCAL_FILE_STORAGE.md) |
| RC1.6 | Synchronous Process & Index | **Implemented** | — | [PROCESS_AND_INDEX.md](backend/PROCESS_AND_INDEX.md) |
| RC1.6 | Explicit knowledge-base Publish | **Implemented** | — | [KNOWLEDGE_MANAGEMENT.md](backend/KNOWLEDGE_MANAGEMENT.md) |
| RC1.6 | Release Version 1.0.0 alignment | **Implemented** | — | [CHANGELOG.md](../CHANGELOG.md) · [RELEASE_NOTES.md](../RELEASE_NOTES.md) |

Full spec catalog: [specs/README.md](../specs/README.md).

## Version 2 — Planned

Not shipped in Version 1.0.0. Details: [Roadmap](ROADMAP.md).

| Topic | Status |
| --- | --- |
| Authentication / real identity | **Version 2** |
| Background workers / job queues | **Version 2** |
| Streaming (SSE / websockets) | **Version 2** |
| Agent tools / LangGraph orchestration | **Version 2** |
| Experiment authoring UI | **Version 2** |
| Provider administration | **Version 2** |
| Multi-node / production deployment | **Version 2** |
| Hybrid search | **Version 2** |

## Shared foundations (Implemented)

| Concern | Doc |
| --- | --- |
| API envelopes / OpenAPI | [API_FOUNDATION.md](backend/API_FOUNDATION.md) |
| Persistence | [PERSISTENCE_LAYER.md](backend/PERSISTENCE_LAYER.md) |
| Application CQRS style | [APPLICATION_LAYER.md](backend/APPLICATION_LAYER.md) |

## Related documents

- [Architecture Summary](ARCHITECTURE_SUMMARY.md)
- [Project Overview](OVERVIEW.md)
- [Evaluation Guide](EVALUATION_GUIDE.md)
- [Roadmap](ROADMAP.md)
- [Documentation index](README.md)
