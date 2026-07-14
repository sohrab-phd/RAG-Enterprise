# Feature Specifications

> **Purpose:** Authoritative behavior contracts for features and epics.  
> **Navigation:** Prefer [docs/FEATURE_MAP.md](../docs/FEATURE_MAP.md) for the Version 1 map.

## Purpose

Each specification describes a discrete feature before or alongside implementation.
Specs are reviewed with architecture, security, and domain input. **Do not** treat
guide pages as replacements for approved specs.

## Spec catalog

| Spec | Description | Status |
| --- | --- | --- |
| [001-knowledge-management](001-knowledge-management/README.md) | Knowledge bases, folders, documents, uploads, versioning | Implemented |
| [002-document-processing](002-document-processing/SPEC.md) | Text extraction and Persian normalization | Draft |
| [003-chunking](003-chunking/SPEC.md) | Rule-based chunk generation | Draft |
| [004-embeddings](004-embeddings/SPEC.md) | Dense embeddings (BGE-M3) and pgvector storage | Implemented |
| [005-retrieval](005-retrieval/SPEC.md) | Dense vector retrieval with metadata filters | Implemented |
| [006-rag-generation](006-rag-generation/SPEC.md) | Grounded answers, citations, abstention | Implemented |
| [007-evaluation-framework](007-evaluation-framework/README.md) | Offline golden-dataset evaluation | Implemented |
| [008-frontend](008-frontend/README.md) | Operator console (Knowledge, Chat, Evaluation, …) | Implemented (console modules); design docs remain authoritative for scope |

## New specifications

Use the template and process described in
[docs/DEVELOPMENT_WORKFLOW.md](../docs/DEVELOPMENT_WORKFLOW.md) and
[`.cursor/rules/documentation.md`](../.cursor/rules/documentation.md).

## Related documents

- [Documentation index](../docs/README.md)
- [Architecture Summary](../docs/ARCHITECTURE_SUMMARY.md)
- [Evaluation Guide](../docs/EVALUATION_GUIDE.md)
- [Root README](../README.md)
