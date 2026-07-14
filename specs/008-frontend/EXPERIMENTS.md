# Experiments Module

> **Spec:** 008-frontend  
> **Authority:** Experiment configuration, history, comparison, and results  
> **Note:** Mirrors Feature 007 experiment artifacts; thin HTTP adapters planned.

## Module purpose

Pin a RAG configuration + golden dataset version, run offline evaluation, inspect per-question results, and compare two runs. Measurement only—no auto-tuning.

---

## Screen X1 — Experiment history

### Purpose

Browse past runs with status and key metrics.

### Wireframe

```text
┌──────────────────────────────────────────────────────────────┐
│ Experiments                              [New experiment]    │
│ Filter KB [All ▾]  Status [All ▾]  Search run/name           │
├──────────────────────────────────────────────────────────────┤
│ Name / ID        Status  Dataset      Recall  MRR   Created  │
│ smoke-topk8      passed  smoke@1.0.0  0.84    0.71  today →  │
│ smoke-topk4      failed  smoke@1.0.0  0.62    0.48  Mon   →  │
└──────────────────────────────────────────────────────────────┘
```

### Components

`PageHeader`, `FiltersBar`, `ExperimentsTable`, `StatusChip`

### States

| State | UI |
| --- | --- |
| Loading | Table skeleton |
| Success | Paginated rows |
| Empty | CTA to New experiment |
| Error | Retry |

### API endpoints

| Action | Planned | Artifact |
| --- | --- | --- |
| List runs | `GET .../evaluations/runs` | `experiments/*/summary.json` + `config.json` |

### Loading / Errors / Empty

Standard table patterns. Show `aggregate_incomplete` failures as `failed` with badge.

---

## Screen X2 — Configure & run

### Purpose

Capture immutable experiment config and start a run.

### Wireframe

```text
┌────────────────────────────────────────────────────────────┐
│ New experiment                                             │
│ Name [smoke-bge-m3-topk8-v1____________]                   │
│ Knowledge base [Policies KB ▾]                             │
│ Dataset id [kb-hr-fa-smoke]  Version [1.0.0]               │
│ Dataset path / registry select (operator input)            │
│                                                            │
│ Embedding model [BAAI/bge-m3]  (read-only if single)       │
│ Chunk size [1000]  Overlap [125]  (documentational pin)    │
│ top_k [8]  Prompt version [v1]  LLM [gpt-4o-mini]          │
│ min_evidence_score [0.25]                                  │
│                                                            │
│ Thresholds                                                 │
│ Recall@K ≥ [0.70]  MRR ≥ [0.50]  Groundedness ≥ [0.70]     │
│ Citation Prec ≥ [0.70]  Abstention Prec ≥ [0.80]           │
│                                                            │
│ [Cancel]                              [Start experiment]   │
└────────────────────────────────────────────────────────────┘
```

### Components

`ExperimentConfigForm`, `ThresholdFields`, `ReadonlyHint`, `ConfirmStartDialog`

### States

| State | UI |
| --- | --- |
| Editing | Form dirty tracking |
| Submitting | Button loading; prevent double submit |
| Running | Redirect to detail with `status=running` poll |
| Validation | Field errors for missing dataset / KB |

### API endpoints

| Action | Planned | Backs onto |
| --- | --- | --- |
| Start run | `POST .../evaluations/runs` | `EvaluationService.create_config` + `run` |
| Dataset catalog (optional) | `GET .../evaluations/datasets` | Known dataset directories |

Config fields match [007 EXPERIMENTS.md](../007-evaluation-framework/EXPERIMENTS.md). UI must not invent new scoring parameters.

### Loading / Errors / Empty

- `dataset_not_found` / `dataset_invalid` → form-level error; do not create empty run.
- `kb_unavailable` → fatal toast; stay on form.

---

## Screen X3 — Run detail / results

### Purpose

Show frozen config, aggregate metrics, and per-question outcomes.

### Wireframe

```text
┌────────────────────────────────────────────────────────────┐
│ smoke-topk8 · run-a1…                          PASSED      │
│ [Config] [Metrics] [Results]                               │
├────────────────────────────────────────────────────────────┤
│ Config (read-only JSON summary / key fields)               │
│ Metrics grid (same tiles as Evaluation)                    │
│ Failing: groundedness                                      │
├────────────────────────────────────────────────────────────┤
│ Results                                                    │
│ QID           Gen status   Recall hit  e2e ms  Err         │
│ hr-leave-001  completed    yes         870     —           │
│ hr-unknown-001 abstained   n/a         120     —           │
│ hr-x          error        —           —       timeout     │
│                                                            │
│ Selected question detail (bottom or side)                  │
│ retrieved_chunk_ids · cited_chunk_ids · answer snippet     │
└────────────────────────────────────────────────────────────┘
```

### Components

`RunHeader`, `TabBar` (Config / Metrics / Results), `ConfigReadonly`, `MetricStatGrid`, `ResultsTable`, `QuestionOutcomeDrawer`

### States

| State | UI |
| --- | --- |
| Running | Progress: “N / M questions” if exposed; else indeterminate |
| Passed / Failed | Final chips + failing metric list |
| Loading artifacts | Tab skeletons |
| Question selected | Drawer with outcome JSON fields |

### API endpoints

| Action | Planned | Artifact |
| --- | --- | --- |
| Get summary | `GET .../runs/{id}` | `summary.json` |
| Get config | `GET .../runs/{id}/config` | `config.json` |
| Get metrics | `GET .../runs/{id}/metrics` | `metrics.json` |
| Get results | `GET .../runs/{id}/results` | `results.jsonl` |

### Loading / Errors / Empty

- Results empty while running → “Run in progress…”
- Partial results OK (fail soft): show error rows.
- Corrupt JSONL line → skip + warning banner count.

---

## Screen X4 — Comparison

### Purpose

Compare two completed runs side by side.

### Wireframe

```text
┌────────────────────────────┬────────────────────────────┐
│ Run A [smoke-topk8 ▾]      │ Run B [smoke-topk4 ▾]      │
│ PASSED                     │ FAILED                     │
│ Recall 0.84                │ Recall 0.62                │
│ MRR    0.71                │ MRR    0.48                │
│ Ground 0.80                │ Ground 0.66                │
│ top_k=8 prompt=v1          │ top_k=4 prompt=v1          │
│ Δ Recall +0.22             │                            │
└────────────────────────────┴────────────────────────────┘
```

### Components

`ComparePicker`, `MetricDiffTable`, `ConfigDiffList`

### States

| State | UI |
| --- | --- |
| Need two runs | Disabled compare until A and B chosen |
| Loading | Dual skeletons |
| Mismatch datasets | Warning: “Datasets differ — compare carefully” |

### API endpoints

Reuse get summary/metrics for `a` and `b`. No dedicated compare API required in v1.

### Loading / Errors / Empty

If either run missing → error on that column.

## Module non-goals

- Parallel hyperparameter sweeps UI
- Auto-select “best” config for production
- Editing past configs in place (new run = new config)
- Charts
