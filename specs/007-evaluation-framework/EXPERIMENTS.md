# Experiments

> **Spec:** 007-evaluation-framework  
> **Authority:** Experiment configuration, execution, and result persistence

## 1. Purpose

An **experiment** pins a full RAG configuration and a golden dataset version, runs every
question, computes metrics, and stores results. Experiments are measurement artifacts —
they do not change production configuration.

## 2. Experiment configuration

| Field | Type | Description |
| --- | --- | --- |
| `experiment_id` | UUID / string | Unique run identity (assigned at create) |
| `name` | string | Human label |
| `organization_id` | UUID | Tenant owning the evaluation |
| `knowledge_base_id` | UUID | Corpus under test |
| `dataset_id` | string | Golden dataset id |
| `dataset_version` | string | Exact dataset version |
| `embedding_model` | string | e.g. `BAAI/bge-m3` |
| `chunk_size` | int | Target chunk chars used when corpus was built |
| `overlap` | int | Chunk overlap chars |
| `top_k` | int | Retrieval K for this run |
| `prompt_version` | string | e.g. `v1` (Feature 006 template) |
| `llm` | string | Pinned `model_key` |
| `min_evidence_score` | float | Generation sufficiency threshold |
| `max_history_messages` | int | Usually `0` for offline single-turn eval |
| `thresholds` | object | Pass/fail gates from [METRICS.md](METRICS.md) |
| `created_at` | datetime | UTC |
| `created_by_user_id` | UUID | Operator |

v1 offline turns are **single-turn** (no conversation history) unless a question tag
requires a fixed mini-history fixture (rare; document in `notes`).

### Example

```json
{
  "name": "smoke-bge-m3-topk8-v1",
  "dataset_id": "kb-hr-fa-smoke",
  "dataset_version": "1.0.0",
  "embedding_model": "BAAI/bge-m3",
  "chunk_size": 1000,
  "overlap": 125,
  "top_k": 8,
  "prompt_version": "v1",
  "llm": "gpt-4o-mini",
  "min_evidence_score": 0.25,
  "thresholds": {
    "recall_at_k": 0.70,
    "mrr": 0.50,
    "groundedness": 0.70,
    "citation_precision_mean": 0.70,
    "abstention_precision": 0.80
  }
}
```

Configuration is **immutable** after the run starts. A new tuning attempt = new experiment.

---

## 3. Execution flow

```text
1. Load dataset version
2. Mark evaluation status → running
3. For each question (sequential in v1):
     a. Call retrieve(question, kb, top_k)
     b. Call generate(question, kb, top_k)  [or reuse retrieval if wired]
     c. Record per-question outcome + timings + tokens
4. Aggregate metrics
5. Compare to thresholds → passed | failed
6. Persist aggregate + per-question results
7. Emit EvaluationCompleted (conceptual)
```

| Rule | Description |
| --- | --- |
| One KB | All questions run against the experiment `knowledge_base_id` |
| Fail soft | A single question error is recorded; the run continues |
| Retry | At most 1 retry on transient `model_unavailable` / timeout per question |
| No mutation | Runner never changes indexes, prompts, or production config |
| Auth | System/eval actor with KB read permission and `organization:evaluation:manage` |

Sequential execution is required in v1 for simplicity and rate-limit safety.

---

## 4. Per-question outcome record

```json
{
  "question_id": "hr-leave-001",
  "status": "ok",
  "retrieved_chunk_ids": ["..."],
  "generation_status": "completed",
  "answer": "...",
  "cited_chunk_ids": ["..."],
  "abstained": false,
  "retrieval_latency_ms": 45,
  "generation_latency_ms": 820,
  "e2e_latency_ms": 870,
  "prompt_tokens": 1200,
  "completion_tokens": 180,
  "error_code": null
}
```

---

## 5. Persistence

### 5.1 What is stored

| Artifact | Content |
| --- | --- |
| Experiment config snapshot | Frozen JSON of Section 2 |
| Per-question outcomes | JSONL |
| Aggregate metrics | JSON ([METRICS.md](METRICS.md) report shape) |
| Pass/fail | `passed` \| `failed` plus failing metric list |

### 5.2 Storage layout (conceptual)

```text
evaluation/{experiment_id}/
  config.json
  results.jsonl
  metrics.json
  summary.json
```

PostgreSQL (future implementation) holds Evaluation row metadata:
`organization_id`, `knowledge_base_id`, status lifecycle, paths to artifacts,
`dataset_version`, timestamps — consistent with
[DATA_ARCHITECTURE.md](../../docs/data/DATA_ARCHITECTURE.md).

### 5.3 Lifecycle

Uses existing Evaluation states:

`defined` → `running` → `passed` / `failed` → `archived`

---

## 6. Runner interface (contract only)

```text
EvaluationRunner.run(experiment_id) -> EvaluationSummary
```

Inputs: persisted experiment config + dataset.  
Outputs: summary with metrics and status.  
No HTTP API required in this design phase (CLI/worker later).

---

## 7. Failure handling

| Code | Behavior |
| --- | --- |
| `dataset_not_found` | Fail run immediately |
| `kb_unavailable` | Fail run immediately |
| `question_error` | Record error on that question; continue |
| `aggregate_incomplete` | Fail if &gt; 10% questions errored (configurable) |

---

## 8. Out of scope

- Parallel sweep of many hyperparameter grids
- Auto-selecting “best” experiment for production
- Dashboards / charts
- Comparing against external vendor benchmarks
