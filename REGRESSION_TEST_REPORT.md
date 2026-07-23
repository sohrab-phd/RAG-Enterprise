# REGRESSION_TEST_REPORT.md — RC3.7

| Bug ID | Regression Test Name | Type | Location | Result | Related RC | Coverage Notes |
| --- | --- | --- | --- | --- | --- | --- |
| BUG-RC37-001 | `test_golden_source_marker_matches_normalized_document_text` | Unit | `backend/tests/e2e/test_golden_normalization_alignment.py` | PASS | RC1.3 / Feature 002 / RC3.7 | Ensures golden marker uses Latin digits present in normalized document text |
| BUG-RC37-001 | `test_persian_digits_in_source_document_normalize_to_latin` | Unit | same | PASS | Feature 002 | Locks authoring-vs-storage digit conversion |
| BUG-RC37-001 | `test_rag_happy_path_persian_leave_policy` | End-to-End | `backend/tests/e2e/test_rag_happy_path.py` | PASS | RC1.3 | Full KB→upload→index→retrieve→chat→cite path |
| BUG-RC37-002 | `test_result_rowcount_reads_cursor_attribute` | Unit | `backend/tests/db/test_result_utils.py` | PASS | RC3.7 | Documents helper contract |
| BUG-RC37-002 | `test_result_rowcount_treats_missing_or_none_as_zero` | Unit | same | PASS | RC3.7 | Null/missing safety |
| BUG-RC37-002 | Existing delete cascade suites | Integration | `tests/knowledge/test_delete_*.py` | PASS | RC2.x | Confirms repositories still return delete counts correctly after helper swap |
| BUG-RC37-003 | N/A (style-only) | — | — | — | RC3.7 | Protected by `ruff check` / `ruff format --check` in CI |

### Gate re-runs

| Suite | Command | Result |
| --- | --- | --- |
| Backend full | `uv run pytest -q` | PASS (1 skip: optional Postgres harness DSN) |
| Frontend | `npm test -- --run` | PASS 15/15 |
| Ruff | `uv run ruff check .` + format check | PASS |
| MyPy | `uv run mypy src` | PASS |
| Golestan live | `tools/rc36_evidence_eval.py` → `eval-artifacts/rc37-golestan-regression.json` | PASS (retrieval stable; gen Pass 14/20) |
| API smoke | `tools/rc37_api_smoke.py` | PASS 8/8 |
