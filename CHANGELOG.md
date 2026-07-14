# Changelog

All notable changes to RAG-enterprise are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-07-15

### Highlights

- Enterprise RAG platform (monorepo: FastAPI backend + React operator console)
- Persian document support (demo corpus and language-aware processing)
- Knowledge management (knowledge bases, folders, documents, uploads, versions)
- Document processing (extraction and normalization)
- Chunking
- Embeddings (dense vectors / pgvector path)
- Retrieval (dense cosine search)
- Grounded chat with citations and abstention
- Evaluation framework (offline golden-dataset experiments)
- Evaluation dashboard (operator console)
- Health endpoints (`/live`, `/ready`, `/system`)
- Local filesystem storage for uploads
- One-click Process & Index (synchronous operator action)
- Publish workflow for knowledge bases (`draft` → `active`)

### Known limitations

- No authentication (planned for V2)
- No background workers
- Offline evaluation only
- Local filesystem storage only
- Single-node deployment

[1.0.0]: https://github.com/sohrab-phd/RAG-Enterprise/releases/tag/v1.0.0
