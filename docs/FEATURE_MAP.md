# Feature Map

> **Purpose:** Navigate Version 1 capabilities without opening every folder.  
> **Authority:** Behavior details live in `specs/` and backend module docs—this page only maps them.

## Purpose

Show which features exist in Version 1, their specification entry points, and the
backend documentation that describes the shipped implementation notes.

## Spec map (001–008)

| Spec | Capability | Spec entry | Backend notes |
| --- | --- | --- | --- |
| 001 | Knowledge bases, folders, documents, uploads, versions | [README](../specs/001-knowledge-management/README.md) | [KNOWLEDGE_MANAGEMENT.md](backend/KNOWLEDGE_MANAGEMENT.md) |
| 002 | Document text extraction / Persian normalization | [SPEC](../specs/002-document-processing/SPEC.md) | Processing package (library); see E2E path |
| 003 | Chunk generation | [SPEC](../specs/003-chunking/SPEC.md) | Chunk ORM + indexing path; HTTP worker maturing |
| 004 | Dense embeddings (BGE-M3 / pgvector) | [SPEC](../specs/004-embeddings/SPEC.md) | [EMBEDDINGS_AND_RETRIEVAL.md](backend/EMBEDDINGS_AND_RETRIEVAL.md) |
| 005 | Dense vector retrieval | [SPEC](../specs/005-retrieval/SPEC.md) | same as above |
| 006 | Grounded generation, citations, abstention | [SPEC](../specs/006-rag-generation/SPEC.md) | [RAG_GENERATION.md](backend/RAG_GENERATION.md) |
| 007 | Offline golden-dataset evaluation | [README](../specs/007-evaluation-framework/README.md) | [EVALUATION_FRAMEWORK.md](backend/EVALUATION_FRAMEWORK.md) |
| 008 | Operator console (Knowledge, Chat, Evaluation) | [README](../specs/008-frontend/README.md) | [frontend/README.md](../frontend/README.md) |

Full catalog: [specs/README.md](../specs/README.md).

## Platform release candidates (ops)

| RC | Topic | Doc |
| --- | --- | --- |
| RC1.1 | Configuration validation | [CONFIGURATION.md](backend/CONFIGURATION.md) |
| RC1.2 | `/live`, `/ready`, `/system` | [OPERATIONAL_HEALTH.md](backend/OPERATIONAL_HEALTH.md) |
| RC1.3 | End-to-end happy path test | [E2E_HAPPY_PATH.md](backend/E2E_HAPPY_PATH.md) |
| RC1.4 | Official demo workspace | [Demo Guide](DEMO_GUIDE.md) · [demo/](../demo/README.md) |
| RC1.5 | Documentation polish | [Documentation index](README.md) |

## Shared foundations

| Concern | Doc |
| --- | --- |
| API envelopes / OpenAPI | [API_FOUNDATION.md](backend/API_FOUNDATION.md) |
| Persistence | [PERSISTENCE_LAYER.md](backend/PERSISTENCE_LAYER.md) |
| Application CQRS style | [APPLICATION_LAYER.md](backend/APPLICATION_LAYER.md) |

## Related documents

- [Architecture Summary](ARCHITECTURE_SUMMARY.md)
- [Project Overview](OVERVIEW.md)
- [Evaluation Guide](EVALUATION_GUIDE.md)
- [Documentation index](README.md)
