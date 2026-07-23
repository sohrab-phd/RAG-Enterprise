# RELEASE_CHECKLIST.md — Version 1.0

## Pre-release gates

- [x] Architecture freeze respected (no redesign / no algo “improvements”)
- [x] Backend unit + integration tests green (`uv run pytest`)
- [x] Frontend tests green (`npm test -- --run`)
- [x] Ruff check + format check green
- [x] MyPy `src` green
- [x] RC1.3 Persian E2E happy path green
- [x] Golestan retrieval regression: Hit@1/MRR stable
- [x] Evidence selection still active (smaller prompts)
- [x] API live/ready/retrieve/chat smoke green
- [x] Docker Postgres + Redis healthy
- [x] Ollama reachable with selected model `qwen2.5:7b`
- [x] Production bugs from this gate fixed + regression tests added
- [x] Deliverable reports written (RC3.7 + matrix + bugs + tests + perf + checklist)

## Operator launch checklist

- [ ] Docker Desktop running
- [ ] `uv run python run.py` from repo root (or compose + uvicorn + Vite as documented)
- [ ] Confirm `BACKEND_PORT` (default **8800** on this host) and `VITE_API_BASE_URL`
- [ ] Open UI Knowledge → create/publish KB → upload → process → chat
- [ ] Verify citations render and copy works
- [ ] Verify delete document/folder/KB cleans retrieval results

## Release decision

**READY FOR RELEASE** — see `RC3.7_VALIDATION_REPORT.md`.

## Sign-off artifacts

| Artifact | Path |
| --- | --- |
| Validation report | `RC3.7_VALIDATION_REPORT.md` |
| Regression matrix | `REGRESSION_MATRIX.md` |
| Bug fixes | `BUG_FIXES.md` |
| Regression tests | `REGRESSION_TEST_REPORT.md` |
| Performance | `PERFORMANCE_REPORT.md` |
| Backend pytest log | `eval-artifacts/rc37-backend-pytest-final.txt` |
| Frontend vitest log | `eval-artifacts/rc37-frontend-vitest.txt` |
| Golestan regression | `eval-artifacts/rc37-golestan-regression.json` |
| Evidence diagnostics | `eval-artifacts/rc37-evidence-selection.json` |
| API smoke | `eval-artifacts/rc37-api-smoke.json` |
