# End-to-End Happy Path (RC1.3)

> **Status:** Implemented  
> **Scope:** One automated golden-path scenario covering the RAG pipeline with a
> realistic Persian company policy document. No frontend. No mocked business services.

## Scenario (single workflow)

```text
Start application
  → Create Knowledge Base (activate via archive → restore)
  → Upload Persian sample document
  → Document processing (DocumentProcessingService)
  → Chunk generation
  → Embedding + Indexing (IndexingService)
  → Ask Persian question
  → Retrieve evidence
  → Generate grounded answer (LLM echo in CI)
  → Validate citations + evaluation engine
  → Pass
```

## Artifacts

| Artifact | Path |
| --- | --- |
| Automated test | `backend/tests/e2e/test_rag_happy_path.py` |
| Sample document | `backend/tests/e2e/fixtures/company_leave_policy_fa.txt` |
| Expected question / answer pattern | `backend/tests/e2e/fixtures/golden_path.json` |
| Pipeline bridge helper | `backend/tests/e2e/helpers/pipeline.py` |

### Golden expectations

From `golden_path.json`:

- **Question:** مرخصی استحقاقی سالانه کارکنان رسمی چند روز کاری است؟
- **Expected answer (Persian ground truth):** مرخصی استحقاقی سالانه کارکنان رسمی ۲۰ روز کاری است.
- **Answer pattern (`LLM_BACKEND=echo`):** `Based on the retrieved evidence, here is the answer. [1]`
- **Source must contain:** `۲۰ روز کاری`

## Assertions

The scenario passes only when:

- all HTTP steps succeed (`201`/`200` as applicable),
- the chat turn is **not** abstained (`status=completed`),
- at least one citation is returned,
- every citation `chunk_id` is present in the chat `retrieved_chunks`,
- evaluation metrics `is_grounded` / `is_citation_accurate` pass,
- `EvaluationService.run` completes with `error_count=0` and no failing thresholds.

## Providers used in CI

| Concern | Setting | Value |
| --- | --- | --- |
| LLM | `LLM_BACKEND` | `echo` (no external call) |
| Embedding | `EMBEDDING_BACKEND` | `deterministic` |
| Evidence gate | `GENERATION_MIN_EVIDENCE_SCORE` | `0.0` (deterministic vectors are not semantic) |
| Database | `DATABASE_URL` | sqlite+aiosqlite memory |

## Known orchestration gap

Public HTTP APIs currently stop at `processing_status=uploaded`. There is no worker
endpoint for extraction/chunking/indexing yet. RC1.3 therefore:

1. uses **existing HTTP APIs** for create KB, upload, retrieve, and chat;
2. advances the version with **real** `DocumentProcessingService` + `IndexingService`
   in-process (see `advance_uploaded_version_to_indexed`);
3. does **not** mock retrieval, generation, indexing, or evaluation services.

Knowledge bases are created as `draft`; retrieval requires `active`. The golden path
activates an empty KB via `POST .../archive` then `POST .../restore` before uploads
(no new publish endpoint).

## Run

```bash
cd backend
uv run pytest tests/e2e/test_rag_happy_path.py -q
```

## Related documents

- [Operational Health (RC1.2)](OPERATIONAL_HEALTH.md)
- [Configuration Validation (RC1.1)](CONFIGURATION.md)
- [Evaluation Framework](EVALUATION_FRAMEWORK.md)
- [API Foundation](API_FOUNDATION.md)
- [Architecture](../ARCHITECTURE.md)
