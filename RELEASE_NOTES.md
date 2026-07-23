# RAG-enterprise v1.0.0 — Release Notes

**Product:** Enterprise Persian RAG System  
**Version:** 1.0.0  
**Tag:** `v1.0.0`  
**Date:** 2026-07-23  
**Status:** Official Version 1.0 release

## Summary

Version 1.0.0 delivers a production-ready, locally operable enterprise RAG
platform optimized for Persian knowledge bases: curated KB/folder/document
management, hybrid retrieval, deterministic evidence selection, grounded chat
with citations, offline evaluation, and a one-command developer launcher.

## Major features

- End-to-end RAG loop: ingest → process → embed → retrieve → select evidence → generate → cite
- Operator console for Knowledge, Upload/Process, Chat, Evaluation, and Settings
- Explicit knowledge-base publish workflow (`draft` → `active`)
- Synchronous Process & Index for operator-controlled indexing
- Persian-first processing and bilingual (Persian/English) grounded answers
- Local-first LLM and embedding stack suitable for air-gapped demos

## Architecture

- Modular monorepo with CQRS-style application boundaries and dependency injection
- Backend: FastAPI, SQLAlchemy async, Alembic, PostgreSQL + pgvector, Redis
- Frontend: React + TypeScript + Vite operator console
- Frozen V1 AI pipeline: Hybrid Retrieval → RC3.2 Ranking → RC3.6 Evidence Selection → PromptBuilder → GenerationService
- Durable decisions documented in ADRs under `docs/`; feature contracts in `specs/`

## Supported document formats

| Format | Support in V1.0 |
| --- | --- |
| TXT / plain text | Yes |
| PDF (text layer) | Yes (Persian digit/glyph hardening in RC3.3) |
| DOCX | Yes |
| Scanned / OCR PDF | Out of scope |

## Persian language support

- Persian text normalization (digits, Arabic/Persian letter variants, ZWNJ handling)
- Language-aware processing and FAQ-oriented retrieval signals
- Fluent Persian answer guidance in PromptBuilder (RC3.4) with RC3.1 abstain contract preserved
- Official Persian demo corpus (`demo/`) and Golestan university FAQ benchmark tooling

## Hybrid Retrieval

- Dense vector search (pgvector / cosine) combined with lexical BM25
- Reciprocal Rank Fusion (RRF) to merge candidate lists
- Feeds existing RC3.2 ranking calibration (hybrid does not replace ranking)

## Evidence Selection

- Deterministic heuristic layer after retrieval and before PromptBuilder (RC3.6)
- Labels chunks PRIMARY / SUPPLEMENTARY / IRRELEVANT
- Prompt receives 1–3 primary + 0–2 supplementary chunks; irrelevant discarded
- Reduces prompt size and distractor FAQ answers without ML/cross-encoder/LLM judge

## Ollama Local LLM

- OpenAI-compatible / Ollama provider integration for local generation
- Default validated model path: `qwen2.5:7b` (configurable)
- Mock / echo backends for deterministic tests and CI
- Readiness probes report LLM reachability and selected model

## Knowledge Base management

- Create, rename, list, refresh, publish, and delete knowledge bases
- Validation for empty, duplicate, Unicode/Persian, and long names
- Cascade cleanup of dependent artifacts on delete

## Folder management

- Nested folders and deep hierarchies
- Recursive delete with integrity checks and sibling preservation
- UI + API coverage for selection and empty/non-empty folder cases

## Document management

- Upload sessions, versioning, process & index, re-upload/replace
- Deletion before/after indexing with storage, chunk, and embedding cleanup
- Document counts and orphan-prevention cascade tests

## Launcher

- Single entrypoint: `uv run python run.py`
- Validates developer tools (uv, Docker, Node), starts Compose services, runs migrations, boots backend/frontend
- Meaningful errors for missing Docker Desktop and port conflicts
- Ctrl+C teardown without destroying named volumes by default

## Validation summary (RC3.7)

| Gate | Result |
| --- | --- |
| Backend pytest | PASS |
| Frontend Vitest | PASS |
| Ruff + MyPy | PASS |
| Golestan Hit@1 / MRR | 0.85 / 0.90 |
| API smoke | PASS |
| Release recommendation | **READY FOR RELEASE** |

Details: `RC3.7_VALIDATION_REPORT.md`, `REGRESSION_MATRIX.md`, `PERFORMANCE_REPORT.md`.

## Version metadata

| Surface | Version |
| --- | --- |
| Backend `rag_enterprise.__version__` | `1.0.0` |
| Backend `pyproject.toml` | `1.0.0` |
| Frontend `package.json` | `1.0.0` |
| Git tag | `v1.0.0` |

## Known limitations

- No authentication / multi-user identity beyond development headers (V2)
- No background workers or distributed job queue
- Evaluation **execution** remains offline/filesystem-oriented
- Local filesystem object storage only
- Single-node deployment profile
- OCR / scanned PDFs not supported
- Small local LLMs may still produce partial multi-fact answers despite correct retrieval

## Future Version 2 roadmap

- Authentication, authorization, and audit-ready identity
- Background workers for long-running ingest/index jobs
- Online evaluation runs from the operator console
- Object storage backends (S3-compatible) and multi-node deployment
- Optional learned rerankers / larger model profiles (post-V1)
- Expanded OCR and complex table extraction
- Richer frontend test coverage and soak/concurrency harnesses

## Getting started

1. Copy `.env.example` → `.env` and `backend/.env` as documented
2. Ensure Docker Desktop, uv, Node 20+, and Ollama (with selected model) are available
3. From repository root: `uv run python run.py`
4. Follow [README.md](README.md) and [docs/FIRST_RUN.md](docs/FIRST_RUN.md)

Full change list: [CHANGELOG.md](CHANGELOG.md).
