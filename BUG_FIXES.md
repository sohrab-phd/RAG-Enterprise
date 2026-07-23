# BUG_FIXES.md — RC3.7

## BUG-RC37-001 — E2E golden path digit mismatch

**Description**  
`tests/e2e/test_rag_happy_path.py` failed asserting retrieved chunk text contains `۲۰ روز کاری`.

**Root cause**  
Feature 002 Persian normalization converts Persian/Arabic-Indic digits to Latin before indexing. Stored/retrieved chunk text contains `20 روز کاری`, while `golden_path.json` still required Persian digits.

**Severity**  
P1 High (blocks canonical RC1.3 release E2E)

**Affected subsystem**  
E2E fixtures / validation alignment (not retrieval algorithm)

**Files modified**  
- `backend/tests/e2e/fixtures/golden_path.json`  
- `backend/tests/e2e/test_golden_normalization_alignment.py` (new)

**Fix summary**  
Align golden `source_must_contain` / expected answer digits with post-normalization storage form. Add regression tests that fail if fixtures drift back to Persian digits.

**Risk**  
Low — test/fixture only; production normalization unchanged.

---

## BUG-RC37-002 — MyPy CI gate red

**Description**  
`uv run mypy src` reported 22 errors (SQLAlchemy `Result.rowcount` stubs, unused `type: ignore`, Literal/`str` assignment on embedding provider name).

**Root cause**  
SQLAlchemy typing stubs expose `Result` without `rowcount`; several ignore comments became unused after stub/tooling updates; `provider_name` inferred as Literal then widened to `str`.

**Severity**  
P1 High (CI required check)

**Affected subsystem**  
Typing / repository delete helpers / provider inventory descriptors

**Files modified**  
- `backend/src/rag_enterprise/db/result_utils.py` (new)  
- `backend/src/rag_enterprise/indexing/repositories/chunk.py`  
- `backend/src/rag_enterprise/indexing/repositories/embedding.py`  
- `backend/src/rag_enterprise/generation/repositories.py`  
- `backend/src/rag_enterprise/knowledge/repositories/document.py`  
- `backend/src/rag_enterprise/knowledge/repositories/document_version.py`  
- `backend/src/rag_enterprise/knowledge/repositories/folder.py`  
- `backend/src/rag_enterprise/knowledge/repositories/upload_session.py`  
- `backend/src/rag_enterprise/indexing/providers/factory.py`  
- `backend/src/rag_enterprise/generation/providers/factory.py`  
- `backend/src/rag_enterprise/api/v1/endpoints/health.py`  
- `backend/tests/db/test_result_utils.py` (new)

**Fix summary**  
Introduce `result_rowcount()` helper using `getattr`; annotate `provider_name: str`; remove unused ignores. No runtime semantic change.

**Risk**  
Low — typing-only / equivalent rowcount extraction.

---

## BUG-RC37-003 — Ruff hygiene on health modules

**Description**  
Ruff reported E501/SIM102 and format drift under health endpoints/core.

**Root cause**  
Line length and nested condition style after prior inventory expansions.

**Severity**  
P3 Low

**Files modified**  
- `backend/src/rag_enterprise/core/health.py`  
- related format-only files touched by `ruff format`

**Fix summary**  
Combine nested `if`; format. Behavior unchanged.

**Risk**  
Negligible.
