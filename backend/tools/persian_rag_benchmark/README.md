# Persian RAG Diagnostics & Benchmark Framework

Developer-only suite for **Version 1.0.0** Persian RAG quality.

This package **does not** modify production code, APIs, or business logic. It boots the
same `AppContainer` used by FastAPI and calls production services in-process
(`RetrievalService`, `GenerationService`, `normalize_persian_text`, embedding provider).

Location: `backend/tools/persian_rag_benchmark/`

---

## What it does

1. **Ground truth** — reads indexed Persian chunks for a KB and auto-builds **40–60**
   natural Persian questions per document (balanced categories).
2. **Robustness** — expands each question with Persian surface variants (formal/informal,
   synonyms, ی/ک, نیم‌فاصله, digits ۰/0/٠, punctuation, whitespace).
3. **Pipeline** — runs real retrieve (+ optional generate) against the live corpus.
4. **Diagnostics** — retrieval, chunks, embeddings, generation, Persian language, RCA labels.
5. **Reports** — `diagnostics.json`, `diagnostics.csv`, `diagnostics.html`, `acceptance_v1.json`.

---

## Prerequisites

- Backend dependencies installed (`cd backend && uv sync`)
- Docker Postgres (pgvector) reachable via `backend/.env` `DATABASE_URL`
- An **active** knowledge base with Persian documents already **processed & indexed**

Default actor IDs match the frontend stub:

| Variable | Default |
| --- | --- |
| Organization | `018f0000-0000-7000-8000-000000000001` |
| Workspace | `018f0000-0000-7000-8000-000000000002` |
| User | `018f0000-0000-7000-8000-000000000003` |

---

## How to run

From the `backend/` directory:

```powershell
# Full diagnostics (retrieve + generate + reports)
uv run python -m tools.persian_rag_benchmark `
  --knowledge-base-id 019f62f7-eaa0-7ac5-a518-153afa3f0658

# Dataset only (JSONL ground truth + robustness variants)
uv run python -m tools.persian_rag_benchmark `
  --knowledge-base-id <KB_UUID> `
  --dataset-only

# Retrieval-focused (skip chat generation side effects)
uv run python -m tools.persian_rag_benchmark `
  --knowledge-base-id <KB_UUID> `
  --skip-generation
```

Optional filters:

```powershell
uv run python -m tools.persian_rag_benchmark `
  --knowledge-base-id <KB_UUID> `
  --document-id <DOC_UUID> `
  --questions-min 40 `
  --questions-max 60 `
  --robustness-variants 8 `
  --top-k 8 `
  --output-dir benchmark-artifacts/persian-rag
```

---

## Artifacts

Each run creates:

```text
benchmark-artifacts/persian-rag/<run-id>/
  dataset/
    manifest.json
    dataset.jsonl          # Feature-007-compatible + extended Persian fields
  diagnostics.json
  diagnostics.csv
  diagnostics.html         # RTL Persian-friendly HTML dashboard
  acceptance_v1.json       # Version 1.0.0 readiness + ranked recommendations
```

Open `diagnostics.html` in a browser for overall health, subsystem scores, failed examples,
and root-cause explanations.

---

## Failure labels

| Label | Meaning |
| --- | --- |
| `DOCUMENT_EXTRACTION` | Extracted text quality issue |
| `TEXT_NORMALIZATION` | Arabic/Persian letter mismatch |
| `UNICODE_NORMALIZATION` | NFC/NFKC mismatch |
| `HALFSPACE_NORMALIZATION` | ZWNJ / نیم‌فاصله drift |
| `LANGUAGE_DETECTION` | Persian not detected |
| `CHUNKING` | Boundary / fragment issue |
| `EMBEDDING` | Robustness variants disagree on top chunk |
| `RETRIEVAL` / `WRONG_CHUNK` / `WRONG_DOCUMENT` | Missed gold evidence |
| `LOW_RETRIEVAL_SCORE` | Weak similarity |
| `GENERATION` / `CITATION` | Answer / citation quality |
| `UNKNOWN` | Needs manual review |

---

## Design notes

- Prefer **Persian-specific** probes over generic English metrics.
- Reuse Feature 007 metric ideas (`Recall@k`, `MRR`, groundedness/citation) but add Persian
  surface and robustness analysis that production evaluation does not cover.
- Ground-truth generation is **deterministic/heuristic** from chunk text so the tool works
  with `LLM_BACKEND=echo` / `EMBEDDING_BACKEND=deterministic` for local regression.
- `GenerationService.generate` persists conversations — use a dedicated demo KB or
  `--skip-generation` when you want read-mostly diagnostics.
- This is the intended **official regression suite** for every Version 1.x / 2 Persian change:
  regenerate dataset → run benchmark → compare HTML/acceptance scores.

---

## Tests

```powershell
cd backend
uv run pytest tests/tools/persian_rag_benchmark -q
```
