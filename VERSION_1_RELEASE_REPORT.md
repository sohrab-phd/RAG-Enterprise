# Version 1.0 Release Report

**Product:** Enterprise Persian RAG System (RAG-enterprise)  
**Prepared:** 2026-07-23  
**Scope:** Local release preparation only (no push, no GitHub release publish)

## Repository state

| Field | Value |
| --- | --- |
| Current branch | `main` |
| Release tag | `v1.0.0` (annotated) |
| Tag message | `Enterprise Persian RAG System Version 1.0` |
| Resolve commit | `git rev-parse v1.0.0^{commit}` |
| Remote tracking | `origin/main` — local `main` is ahead; **not pushed** |
| Working tree | Clean at release preparation completion |

## Tag created

| Field | Value |
| --- | --- |
| Tag | `v1.0.0` |
| Type | Annotated |
| Message | `Enterprise Persian RAG System Version 1.0` |
| Prior tag note | Older local `v1.0.0` (2026-07-15, RC1.6) was replaced to point at completed V1.0 |

## Release summary

Version **1.0.0** is the official freeze of the enterprise Persian RAG platform:

- Knowledge / folder / document management with publish and cascade delete
- TXT, PDF (text-layer), and DOCX ingestion
- Persian normalization and bilingual grounded chat
- Hybrid retrieval (dense + BM25 + RRF) and RC3.2 ranking
- RC3.6 evidence selection before prompting
- Ollama-backed local generation with citations and abstention
- Offline evaluation framework and operator console
- One-command launcher (`uv run python run.py`)
- RC3.7 validation: READY FOR RELEASE

Version metadata already aligned at `1.0.0` in:

- `backend/src/rag_enterprise/__init__.py`
- `backend/pyproject.toml`
- `frontend/package.json`

## Documents updated for this release

| File | Action |
| --- | --- |
| `CHANGELOG.md` | Updated `[1.0.0] — 2026-07-23` with full V1 feature set |
| `RELEASE_NOTES.md` | Rewritten with required V1.0 sections |
| `VERSION_1_RELEASE_REPORT.md` | This report |

## Release checklist

- [x] Verify working tree clean (before doc updates)
- [x] Review version references (`1.0.0` on backend/frontend)
- [x] Update `CHANGELOG.md`
- [x] Update `RELEASE_NOTES.md`
- [x] Commit release documentation (local)
- [x] Recreate annotated tag `v1.0.0` on release commit
- [x] Produce this report
- [ ] Push `main` (explicitly **not** done)
- [ ] Push tag `v1.0.0` (explicitly **not** done)
- [ ] Create GitHub Release UI entry (explicitly **not** done)

## Final tag target

| Field | Value |
| --- | --- |
| Branch | `main` |
| Tag | `v1.0.0` |
| Tag message | `Enterprise Persian RAG System Version 1.0` |
| Commit | Resolve with `git rev-parse v1.0.0^{commit}` (must match `HEAD` when tree is clean) |

## Related artifacts

- `RC3.7_VALIDATION_REPORT.md`
- `REGRESSION_MATRIX.md`
- `BUG_FIXES.md`
- `REGRESSION_TEST_REPORT.md`
- `PERFORMANCE_REPORT.md`
- `RELEASE_CHECKLIST.md`
- `REPOSITORY_CLEANUP_REPORT.md`
