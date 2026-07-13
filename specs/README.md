# Feature Specifications

> **Status:** Placeholder directory for feature-level specifications.

## Purpose

Each specification in this directory describes a discrete feature or epic before implementation begins. Specs should be reviewed by the Architect, Security, and relevant domain agents.

## Specification Template

<!-- TODO: Copy this template for each new spec file -->

```markdown
# [Feature Name]

## Status
Draft | Review | Approved | Implemented

## Summary
<!-- One paragraph description -->

## Motivation
<!-- Why are we building this? -->

## Requirements
### Functional
<!-- TODO -->

### Non-Functional
<!-- TODO: performance, security, observability -->

## API Contract (if applicable)
<!-- TODO -->

## Data Model (if applicable)
<!-- TODO -->

## Dependencies
<!-- TODO: upstream/downstream systems -->

## Open Questions
<!-- TODO -->
```

## Planned Specifications

| Spec | Description | Status |
|------|-------------|--------|
| [001-knowledge-management](001-knowledge-management/README.md) | Knowledge bases, folders, documents, uploads, and versioning | Implemented |
| [002-document-processing](002-document-processing/SPEC.md) | Text extraction and Persian normalization for uploads | Draft |
| [003-chunking](003-chunking/SPEC.md) | Rule-based chunk generation for embeddings | Draft |
| [004-embeddings](004-embeddings/SPEC.md) | Dense embeddings with BGE-M3 and pgvector storage | Implemented |
| [005-retrieval](005-retrieval/SPEC.md) | Dense vector retrieval with metadata filters | Implemented |
| `authentication.md` | User authentication and session management | TODO |
| `document-ingestion.md` | Upload, parse, and chunk documents | TODO |
| `vector-search.md` | Embedding storage and similarity search | TODO |
| `chat-api.md` | Conversational RAG API | TODO |
| `admin-console.md` | Tenant and knowledge base administration | TODO |
