# RC3.7 — Validation Report (Version 1.0 Release Candidate)

Status: **READY FOR RELEASE**  
Date: 2026-07-23  
Role: Final production quality gate (validate / stabilize / minimal bugfix only)

## Executive Summary

Version 1.0 architecture is treated as frozen (CQRS, DI, APIs, schema, hybrid retrieval, ranking, evidence selection, PromptBuilder, GenerationService, embeddings, Ollama, launcher, frontend).

RC3.7 executed automated backend/frontend suites, Golestan Persian RAG regression, API smoke checks, readiness probes, and lint/type gates. One release-blocking E2E regression was found and fixed (golden fixture digit mismatch after Persian normalization). CI mypy failures were cleared with localized typing helpers (no runtime behavior change).

**Release recommendation: READY FOR RELEASE** for V1.0 with documented known limitations (LLM answer variance on multi-fact questions; optional Postgres integration harness uses a separate test DB URL).

## Validation Matrix

| Area | Method | Result |
| --- | --- | --- |
| Knowledge base management | `tests/knowledge/*` (create/publish/delete/rename/validation) | PASS |
| Folder management | `tests/knowledge/test_delete_folder.py` + related | PASS |
| Document management | delete/upload/process cascade tests | PASS |
| Retrieval / hybrid / ranking | `tests/retrieval/*` + live Golestan Hit@1/MRR | PASS |
| Evidence selection (RC3.6) | unit + live gold-in-selected 0.95 | PASS |
| Generation / citations / abstain | generation tests + Golestan chat | PASS |
| Chat API | live smoke + E2E happy path | PASS |
| API status contracts | `tools/rc37_api_smoke.py` 8/8 | PASS |
| UI (automated) | frontend Vitest 15/15 | PASS |
| UI (manual exhaustive pages) | not fully walked page-by-page in this gate | PARTIAL |
| Launcher / Docker / readiness | docker healthy; `/api/v1/live` + `/ready` OK; launcher code reviewed | PASS |
| Performance measurement | measured (no optimization) | PASS (report filed) |
| RC2.x–RC3.6 regression | automated suites + Golestan + prior RC reports | PASS |
| Backend pytest | full suite green after fixes | PASS |
| Frontend vitest | 3 files / 15 tests | PASS |
| Ruff check/format | clean | PASS |
| MyPy `src` | clean after RC3.7 typing fix | PASS |

## Performance Summary

| Metric | Observed (Golestan ABRU KB) |
| --- | ---: |
| Retrieval latency (avg) | ~471 ms |
| Evidence selection (avg) | ~39 ms |
| Chat / generation (avg) | ~3022 ms |
| End-to-end Q→A (avg) | ~3533 ms |
| Hit@1 / MRR | 0.85 / 0.90 (unchanged vs RC3.5/3.6) |
| Avg selected chunks | 2.45 |
| Prompt size reduction vs top-8 | ~69.6% |
| `/ready` LLM probe | ~10 s (Ollama inventory; readiness only) |

See `PERFORMANCE_REPORT.md` for details. No algorithm optimization performed.

## Bugs Found

| ID | Severity | Summary |
| --- | --- | --- |
| BUG-RC37-001 | P1 | RC1.3 E2E happy path failed: golden `source_must_contain` used Persian digits (`۲۰`) while indexed text stores Latin (`20`) after Feature 002 normalization |
| BUG-RC37-002 | P1 | `uv run mypy src` failed CI gate (22 typing errors: SQLAlchemy `rowcount`, unused ignores, Literal/`str` assignment) |
| BUG-RC37-003 | P3 | Ruff SIM102 / E501 / format drift in health modules (release hygiene) |

## Bugs Fixed

| ID | Fix |
| --- | --- |
| BUG-RC37-001 | Updated `golden_path.json` markers to normalized Latin digits; added `test_golden_normalization_alignment.py` |
| BUG-RC37-002 | Added `db/result_utils.result_rowcount`; replaced unsafe `.rowcount` sites; fixed provider typing / unused ignores |
| BUG-RC37-003 | Ruff format + combine nested `if` in `core/health.py` |

Details: `BUG_FIXES.md`, `REGRESSION_TEST_REPORT.md`.

## Remaining Known Limitations

1. **LLM answer completeness variance** — Golestan Pass ≈ 14–16/20 under `qwen2.5:7b`; multi-fact Partial/Fail (e.g. q19) can remain without retrieval regression.
2. **Postgres integration optional test** defaults to `localhost:5432/rag_enterprise_test`, not the compose `5433` app DB — skipped unless that DSN exists (`RUN_POSTGRES_TESTS=1`).
3. **Manual UI exhaustive checklist** (every toast/disabled state on every page) not fully executed in this gate; covered by Vitest + API/backend contracts.
4. **Auth model** remains development header-based identity (as designed for V1).
5. **VRAM / precise CPU sampling** not instrumented in-process; report uses latency proxies and readiness probes.

## Risk Assessment

| Risk | Level | Mitigation |
| --- | --- | --- |
| False abstain / incomplete Persian answers on 7B | Medium | RC3.1–3.6 mitigations; documented V1 limitation |
| CI flake from Ollama latency | Low | readiness timeout; mock LLM in unit/E2E |
| Orphan data on delete | Low | cascade tests for KB/folder/document |
| Hybrid/evidence regressions | Low | Hit@1/MRR stable; gold-in-selected 0.95 |

## Release Recommendation

### READY FOR RELEASE

Reasoning:

- Architecture frozen; no unauthorized redesign.
- Full backend pytest green (1 intentional Postgres-harness skip).
- Frontend Vitest green.
- Ruff + MyPy green (CI-critical).
- Canonical Persian E2E happy path green after fixture alignment.
- Live Golestan retrieval quality unchanged (Hit@1 0.85, MRR 0.90).
- Evidence selection still reducing prompt size (~70%) with ~39 ms overhead.
- API smoke (live/ready/retrieve/chat/404/422) passed 8/8.
- Production bugs found in this gate were fixed with automated regression protection.

Ship Version 1.0 with the known limitations above; defer quality improvements to post-1.0 only if product requires higher Golestan Pass under larger models.
