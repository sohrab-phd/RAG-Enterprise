# Changelog

All notable changes to RAG-enterprise are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-07-23

Official Version 1.0.0 of the Enterprise Persian RAG System.

### Added

- Enterprise RAG monorepo: FastAPI backend + React/Vite operator console
- Knowledge base management (create, rename, publish `draft` → `active`, delete)
- Folder management (nested folders, recursive delete, cascade cleanup)
- Document management (upload, version, process & index, replace, delete)
- Document formats: TXT, PDF (text-layer), DOCX
- Persian language support: normalization, ZWNJ-safe tokenization, bilingual chat
- Chunking and dense embeddings (`BAAI/bge-m3` / sentence-transformers path)
- Hybrid retrieval: dense cosine + BM25 + Reciprocal Rank Fusion (RC3.5)
- Deterministic Persian ranking calibration (RC3.2)
- Evidence selection layer before PromptBuilder (RC3.6)
- Grounded generation with citations, abstention, and conflict reporting
- Local LLM via Ollama (default `qwen2.5:7b`) with mock/deterministic test backends
- Offline evaluation framework and operator evaluation views
- Health probes: `/api/v1/live`, `/ready`, `/system`
- One-command developer launcher (`uv run python run.py`) with Docker Compose
- Official Persian demo corpus and Golestan validation tooling
- RC3.7 production validation gate (automated suites + release reports)

### Known limitations

- No end-user authentication (planned for V2)
- No background workers / async job queue
- Offline evaluation execution (dashboard does not run remote experiments)
- Local filesystem storage only
- Single-node deployment
- Text-layer PDFs only (scanned/OCR out of scope)
- Answer completeness under small local LLMs remains model-bound

[1.0.0]: https://github.com/sohrab-phd/RAG-Enterprise/releases/tag/v1.0.0
