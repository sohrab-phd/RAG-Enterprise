# Project Overview

> **Audience:** newcomers, reviewers, stakeholders  
> **Version:** 1.0.0

## Purpose

RAG-enterprise is a monorepo for a production-oriented **Retrieval-Augmented
Generation** platform: curated knowledge bases, dense retrieval, grounded chat with
citations (or abstention), offline evaluation, and an operator console.

Version 1.0.0 ships a working knowledge → retrieve → generate → evaluate loop with
a public Persian **demo** corpus. Authentication, background workers, streaming,
agent tools, and multi-node deployment are **Version 2** ([Roadmap](ROADMAP.md)).

## Who it is for

| Audience | Typical need |
| --- | --- |
| Platform engineers | Run API locally, extend backend modules |
| Frontend engineers | Operator console (Knowledge, Chat, Evaluation) |
| Quality / AI engineers | Golden datasets and Feature 007 experiments |
| Reviewers | Demo workspace + architecture summary |

## What Version 1.0.0 includes

- Knowledge bases, documents, uploads, and versions (Feature 001)
- Embeddings and dense retrieval (Features 004–005)
- Grounded generation with citations / abstention (Feature 006)
- Offline evaluation framework (Feature 007)
- Operator console modules for Knowledge, Chat, and Evaluation (Feature 008)
- Ops foundations: config validation, health probes, E2E golden path, demo corpus,
  local file storage, Process & Index, and knowledge-base Publish

Details: [Feature Map](FEATURE_MAP.md).

## Repository layout

| Path | Role |
| --- | --- |
| `backend/` | FastAPI application (`uv`) |
| `frontend/` | React operator console (Vite + TypeScript) |
| `demo/` | Official V1 Persian demo knowledge + evaluation set |
| `docs/` | Guides, architecture notes, domain/data docs |
| `specs/` | Feature specifications (authoritative behavior) |
| `infrastructure/` | IaC placeholder; local Compose lives at repo root (multi-node = Version 2) |
| `agents/` / `.cursor/rules/` | AI-assisted engineering governance |

## How to get started

1. [Quick Start](../README.md#quick-start) on the root README  
2. Full local setup: [Development Guide](DEVELOPMENT.md)  
3. Try the demo: [Demo Guide](DEMO_GUIDE.md)  
4. System picture: [Architecture Summary](ARCHITECTURE_SUMMARY.md)

## Related documents

- [Documentation index](README.md)
- [Tech Stack](TECH_STACK.md)
- [Roadmap](ROADMAP.md)
- [ADR index](DECISIONS.md)
