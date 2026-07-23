# REPOSITORY_CLEANUP_REPORT.md — Version 1.0

Date: 2026-07-23  
Scope: repository hygiene only — **no source/behavior changes**

## Summary

Local caches, temporary upload/debug trees, and regenerable evaluation/benchmark JSON outputs were removed. Production code, tests, docs, demo data, eval **tools**, launcher, and release reports were preserved.

Approximate disk freed (local working tree, excluding `.venv` / `node_modules`): **~140 MB** (146,666,777 bytes measured on deleted targets).

## Deleted files / directories

### Generated evaluation outputs (already gitignored)

| Path | Approx. size | Reason |
| --- | ---: | --- |
| `eval-artifacts/` | ~1.0 MB | Live RC3.x/RC3.7 JSON/txt dumps, scratch `_*.py` helpers, retrieve previews |
| `backend/benchmark-artifacts/` | ~26.6 MB | Local RC2.x / model-switch run outputs |
| `backend/eval-artifacts/` | empty | Placeholder runtime dir |

Notable contents removed under `eval-artifacts/` (regenerable via `backend/tools/rc3*_*.py`):

- `rc32`–`rc37` JSON / pytest / vitest logs  
- `evidence_selection*.json`  
- scratch scripts: `_compact.py`, `_dump_results.py`, `_score_report.py`, `_show_retrieve.py`, `_write_previews.py`  
- ad-hoc `retrieve-q*.json`, `golestan-extracted.txt`, nested `golestan-live-eval/`

### Tooling caches (gitignored)

| Path | Approx. size | Reason |
| --- | ---: | --- |
| `backend/.mypy_cache/` | ~110 MB | MyPy cache |
| `backend/.ruff_cache/` | ~39 KB | Ruff cache |
| `backend/.pytest_cache/` | ~28 KB | Pytest cache |
| `.pytest_cache/` | &lt;1 KB | Root pytest cache |
| `backend/src/**/__pycache__/`, `backend/tests/**/__pycache__/`, `tools/**/__pycache__/` | small | Bytecode caches |

### Temporary / runtime local data

| Path | Approx. size | Reason |
| --- | ---: | --- |
| `backend/.tmp-rc37-eval/` | ~0 | RC3.7 debug leftover |
| `backend/.tmp-rc37-uploads/` | ~9 KB | Accidental RC3.7 ASGI debug uploads (**were tracked in git** — removed from tree) |
| `backend/storage/` | ~1.0 MB | Local upload/runtime storage (gitignored) |
| `frontend/dist/` | ~1.0 MB | Frontend build output (gitignored) |

### Not deleted (intentionally)

- `.venv/` / `frontend/node_modules/` — local dependency installs (recreate with `uv sync` / `npm install`)  
- All `backend/src/**` production modules  
- All tests, demo datasets, `backend/tools/rc3*_*.py`, `persian_rag_benchmark/`  
- Root release docs (`RC3.*`, `CHANGELOG.md`, `RELEASE_NOTES.md`, RC3.7 reports)  
- `docs/`, `specs/`, `agents/`, launcher (`run.py`, `tools/dev_launcher/`)

## Moved files

**None.** No files were relocated in this cleanup (avoids breaking doc links without review).

## Archived files

**None.** Regenerable local artifacts were deleted rather than zipped. Release narrative remains in committed markdown reports (`RC3.*_*.md`, `RC3.7_VALIDATION_REPORT.md`, etc.).

## Files requiring manual review

| Item | Recommendation |
| --- | --- |
| Root `RC3.1`–`RC3.7` / `BUG_FIXES.md` / `PERFORMANCE_REPORT.md` / `REGRESSION_*.md` / `RELEASE_CHECKLIST.md` | Keep for V1.0. Optionally later move under `docs/releases/` in a docs-only PR (update README links). |
| `REPOSITORY_TREE.txt` | New snapshot from this cleanup; keep or fold into docs. |
| `tests/README.md` (repo-root `tests/`) | Placeholder pointer only — confirm whether to keep vs rely solely on `backend/tests/`. |
| `scripts/dev-up.*` vs `run.py` / `tools/dev_launcher` | Overlapping launch helpers — keep both for now; consolidate only with explicit docs PR. |
| `.cursor/` | Local IDE/agent rules — not deleted; ensure secrets never land here. |
| CI integration job TODO in `.github/workflows/ci.yml` | Process/docs item, not cleanup. |
| Whether to commit removal of tracked `backend/.tmp-rc37-uploads/**` | **Yes recommended** — those paths should never have been versioned. |

## `.gitignore` updates

Extended ignore patterns (no runtime behavior impact):

- `backend/.tmp-*/`
- `frontend/dist/`
- `frontend/coverage/`
- `frontend/.vite/`

## Repository size reduction

| Category | Freed (approx.) |
| --- | ---: |
| MyPy cache | ~110 MB |
| Benchmark artifacts | ~27 MB |
| Eval artifacts + storage + frontend dist + tmp | ~3 MB |
| Pytest/ruff/pycache | &lt;1 MB |
| **Total measured on deleted targets** | **~140 MB** |

Still large locally if present (unchanged on purpose):

- `backend/.venv` ≈ 1.26 GB  
- `frontend/node_modules` ≈ hundreds of MB  

## Behavior verification

- No production source modules edited.  
- No API/schema/CQRS/DI/retrieval/generation changes.  
- Only hygiene: deletes of local/generated paths + `.gitignore` ignore expansions.  
- Working tree now shows deletion of previously tracked `.tmp-rc37-uploads` files (safe accidental-commit cleanup).

## Updated repository tree

See committed/workspace file: [`REPOSITORY_TREE.txt`](REPOSITORY_TREE.txt) (depth-3 snapshot, excluding `.git`, `.venv`, `node_modules`, caches).

High-level:

```text
RAG Project/
├── .github/
├── agents/
├── backend/          # src, tests, alembic, tools (eval scripts kept)
├── demo/
├── docs/
├── frontend/
├── infrastructure/
├── scripts/
├── specs/
├── tests/            # root pointer README only
├── tools/            # launcher
├── RC3.* / RC3.7 / release markdown
├── CHANGELOG.md, RELEASE_NOTES.md, README.md, run.py
└── REPOSITORY_TREE.txt / REPOSITORY_CLEANUP_REPORT.md
```

## Recommendations for future organization

1. **Never commit** `storage/`, `eval-artifacts/`, `benchmark-artifacts/`, or `backend/.tmp-*` (now ignored more tightly).  
2. Keep live eval outputs out of git; store release evidence only in markdown reports or a tagged CI artifact.  
3. Consider `docs/releases/v1.0/` for RC reports after V1 ship (link updates in a docs-only change).  
4. Prefer `uv run python run.py` as the single documented launcher; mark `scripts/dev-up.*` as legacy if redundant.  
5. Periodically purge local `.mypy_cache` / `.ruff_cache` / `__pycache__` (or rely on ignore + clean scripts).  
6. Do not vendor `.venv` / `node_modules`; document `uv sync` + `npm install` only.
