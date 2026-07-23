# README Update Report — Version 1.0

Date: 2026-07-23  
Scope: Documentation polish only (no production code changes)

## Summary

The root `README.md` was rewritten as a professional open-source landing page for
**RAG-enterprise Version 1.0.0**, with live UI screenshots, architecture diagrams,
performance highlights, installation/quick start, and documentation links.

## New screenshots

Captured from the running operator console + OpenAPI UI
(`scripts/capture-readme-screenshots.mjs`, system Chrome, viewport 1440×900 @2x).

Stored under `docs/images/`:

| File | Screen |
| --- | --- |
| `01-dashboard-knowledge.png` | Knowledge home (default landing) |
| `02-knowledge-bases.png` | Knowledge base list |
| `03-folder-browser.png` | KB folder / document browser |
| `04-upload.png` | Upload / document create dialog |
| `05-processing.png` | Document / processing inspection |
| `06-chat.png` | Chat workspace |
| `07-citations.png` | Grounded answer with citations + evidence panel |
| `08-swagger.png` | FastAPI Swagger UI (`/docs`) |

Capture helper retained: `scripts/capture-readme-screenshots.mjs` (docs tooling).

## Benchmark figures added

README performance table summarizes RC3.x results:

| Metric | Value shown |
| --- | --- |
| Pass rate | 16/20 (RC3.6 peak) |
| Hit@1 / MRR | 0.85 / 0.90 |
| Avg chat latency | ~2.6 s |
| Evidence selection | ~30–40 ms; ~70% prompt reduction |
| Stack | Hybrid retrieval · BGE-M3 · Ollama `qwen2.5:7b` |

Linked evidence: `RC3.6_EVIDENCE_SELECTION_REPORT.md`, `RC3.7_VALIDATION_REPORT.md`,
`PERFORMANCE_REPORT.md`.

## Documentation improvements

| Item | Change |
| --- | --- |
| `README.md` | Full V1.0 professional rewrite |
| Architecture section | Inline Mermaid + link to `docs/ARCHITECTURE.md` / `architecture-diagrams/` |
| Screenshots gallery | Eight referenced images under `docs/images/` |
| Quick start | Emphasizes `uv run python run.py` |
| Doc links | ARCHITECTURE, FIRST_RUN, CONFIGURATION, DEPLOYMENT |
| Version badges | Version 1.0.0 · Production Ready |
| Example workflow | Create → Upload → Process → Publish → Chat |

## Not changed

- Production application source (`backend/src`, `frontend/src` app code)
- APIs, schema, retrieval/generation behavior
- Git tags / remotes (not part of this task)

## Follow-ups (optional)

- Re-capture screenshots after major UI theme changes
- Add a dedicated marketing architecture PNG export from Mermaid if GitHub Mermaid is disabled in a fork viewer
- Deduplicate `01`/`02` if Knowledge home and list diverge visually later
