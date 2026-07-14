# API Mapping

> **Spec:** 008-frontend  
> **Authority:** Screen → backend endpoint map  
> **Rule:** Use existing `/api/v1` contracts. Do not redesign RAG services. Mark gaps explicitly.

## Conventions

| Item | Value |
| --- | --- |
| Base | `/api/v1` |
| Scope | `/workspaces/{workspace_id}/…` unless noted |
| Envelope | Platform `success` / `data` / `error` |
| Actor (dev) | Headers `X-User-Id`, `X-Organization-Id` |
| Auth product | Out of scope — no login APIs consumed |

---

## Knowledge

| Screen | UI action | Method | Path | Status |
| --- | --- | --- | --- | --- |
| K1 | List KBs | `GET` | `/workspaces/{workspace_id}/knowledge-bases` | Exists |
| K1 | Create KB | `POST` | `/workspaces/{workspace_id}/knowledge-bases` | Exists |
| K2 | Get KB | `GET` | `/workspaces/{workspace_id}/knowledge-bases/{kb_id}` | Exists |
| K2 | List folders | `GET` | `.../knowledge-bases/{kb_id}/folders` | Exists |
| K2 | Create folder | `POST` | `.../knowledge-bases/{kb_id}/folders` | Exists |
| K2 | List documents | `GET` | `.../knowledge-bases/{kb_id}/documents` | Exists |
| K2 | Get document | `GET` | `.../knowledge-bases/{kb_id}/documents/{document_id}` | Exists |
| K3 | Upload session flow | `POST` (+ parts/complete) | Per Knowledge Uploads API | Exists |
| K3 | Create version | `POST` | `.../documents/{document_id}/versions` | Exists |
| K4 | Patch document | `PATCH` | `.../documents/{document_id}` | Exists |
| K4 | Get/Put metadata | `GET`/`PUT` | `.../documents/{document_id}/metadata` | Exists |
| K5 | List versions | `GET` | `.../documents/{document_id}/versions` | Exists |
| K5 | Version status | `GET` | `.../versions/{version_id}/status` | Exists |
| K5 | Download | `GET` | `.../versions/{version_id}/download` | Exists |

Archive / restore / delete / move endpoints exist and map to contextual menus (not separate screens in v1).

---

## Chat

| Screen | UI action | Method | Path | Status |
| --- | --- | --- | --- | --- |
| C1 | Send question | `POST` | `/workspaces/{workspace_id}/chat` | Exists |
| C1 | KB picker | `GET` | `/workspaces/{workspace_id}/knowledge-bases` | Exists |
| C2 | Re-run retrieval (optional) | `POST` | `/workspaces/{workspace_id}/retrieve` | Exists |
| C1 | List conversations | — | — | **Gap** — use client session list or future `GET .../conversations` |

### Chat DTO → UI field map

| Response field | UI |
| --- | --- |
| `answer` | Assistant message body |
| `citations[]` | Citation list + marker highlight |
| `retrieved_chunks[]` | Chunk list + similarity |
| `retrieved_chunks[].score` | Similarity display |
| `abstained` / `status` | Status chip / abstention banner |
| `abstention_reason` / `failure_reason` | Alert copy |
| `model_key` / `prompt_template_version` | Evidence meta |
| `warnings` | Warning chips |
| `conversation_id` | Resume + history key |

---

## Evaluation & Experiments

Feature 007 provides `EvaluationService` + filesystem artifacts. **No HTTP API yet.**

| Screen | UI action | Planned thin adapter | Existing backend source |
| --- | --- | --- | --- |
| E1 / X1 | List runs | `GET /workspaces/{id}/evaluations/runs` | `experiments/*/summary.json` + `config.json` |
| E1 / X3 | Get metrics | `GET .../evaluations/runs/{run_id}/metrics` | `metrics.json` |
| X3 | Get config | `GET .../evaluations/runs/{run_id}/config` | `config.json` |
| X3 | Get results | `GET .../evaluations/runs/{run_id}/results` | `results.jsonl` |
| X2 | Start run | `POST .../evaluations/runs` | `EvaluationService.run` |
| E1 | List datasets (optional) | `GET .../evaluations/datasets` | Dataset directories on disk |

### Adapter constraints (non-negotiable)

1. Adapters are thin HTTP façades over Feature 007 — **no new metrics**, no optimizer.
2. Persistence remains filesystem (or future DB metadata only as already planned in 007).
3. Until adapters ship, Evaluation/Experiments UI shows honest empty + “API pending.”

### Metrics field map

| UI label | JSON path |
| --- | --- |
| Recall@K | `metrics.retrieval.recall_at_k` |
| MRR | `metrics.retrieval.mrr` |
| K | `metrics.retrieval.k` |
| Groundedness | `metrics.generation.groundedness` |
| Citation precision (mean) | `metrics.generation.citation_precision_mean` |
| Citation accuracy | `metrics.generation.citation_accuracy` |
| Abstention precision | `metrics.generation.abstention_precision` |
| Abstention recall | `metrics.generation.abstention_recall` |
| e2e p50/p95/mean | `metrics.latency_ms.*` |
| Tokens mean | `metrics.tokens.total_mean` |
| Pass/fail | `summary.status` / `failing_metrics` |

---

## Settings

| Screen | UI action | Planned thin adapter | Existing source |
| --- | --- | --- | --- |
| S2 | Providers | `GET /api/v1/settings/providers` | Embedding + LLM env/config |
| S3 | Models | `GET /api/v1/settings/models` | `LLM_MODEL_KEY`, generation defaults |
| S4 | Prompts | `GET /api/v1/settings/prompts` (+`/{version}`) | `generation/templates/v1` |
| S5 | System / health | `GET /api/v1/health` (+ optional system) | Health route if present |
| — | Write settings | — | **Out of scope v1** unless ADR adds config service |

Do not call cloud provider management APIs from the browser.

---

## Error mapping (all modules)

| Envelope / HTTP | UI pattern |
| --- | --- |
| `validation_failed` / 422 | Field or form errors |
| `unauthorized` / 401 | Actor stub banner (no login page) |
| `forbidden` / 403 | Inline forbidden state |
| `not_found` / 404 | Empty/not-found page |
| `conflict` / 409 | Conflict message (e.g. duplicate name) |
| Network / timeout | Toast + Retry |
| 5xx | ErrorState + correlation id if present |

---

## Client architecture (when implementing)

```text
UI screens
  → feature hooks
    → typed API client (timeout, cancel, envelope decode)
      → /api/v1/...
```

- No render-time fetches.
- DTOs stop at the API boundary; view models for components.
- Correlation: forward or generate `X-Correlation-ID`.

## Gap summary

| Gap | Blocks | Resolution |
| --- | --- | --- |
| Evaluation HTTP | Evaluation, Experiments | Thin adapter over Feature 007 |
| Conversation list HTTP | Chat sidebar longevity | Session list or future GET |
| Settings HTTP | Settings module | Thin read adapters over config |
| Auth | — | Explicitly out of scope |

Nothing in this gap list requires redesigning retrieval, generation, or knowledge domains.
