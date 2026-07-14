# RAG-enterprise v1.0.0

Official Version 1.0.0 release of the RAG-enterprise platform.

## Summary

Version 1.0.0 ships an end-to-end enterprise RAG loop: curated knowledge bases,
document ingestion, dense retrieval, grounded chat with citations, offline
evaluation, and an operator console—plus a public Persian demo corpus.

## Highlights

- Enterprise RAG platform (backend + operator console)
- Persian document support
- Knowledge management, processing, chunking, embeddings, and retrieval
- Grounded chat with citations / abstention
- Evaluation framework and dashboard
- Health probes (`/live`, `/ready`, `/system`)
- Local filesystem upload storage
- Synchronous Process & Index operator action
- Explicit knowledge-base Publish workflow (`draft` → `active`)

## Version metadata

| Surface | Version |
| --- | --- |
| Backend (`rag_enterprise.__version__`) | `1.0.0` |
| OpenAPI / FastAPI | `1.0.0` |
| Frontend (`package.json`) | `1.0.0` |
| Platform docs | Version 1.0.0 |

## Known limitations

- No authentication (planned for V2)
- No background workers
- Offline evaluation only
- Local filesystem storage only
- Single-node deployment

## Getting started

See the [repository README](README.md) quick start and the
[Documentation index](docs/README.md).

Full change list: [CHANGELOG.md](CHANGELOG.md).
