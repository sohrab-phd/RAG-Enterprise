# Evaluation Module

> **Spec:** 008-frontend  
> **Authority:** Offline evaluation overview — metrics and recent runs  
> **Note:** Feature 007 engine exists; HTTP list/read adapters are planned (see API_MAPPING). UI does not redesign metrics.

## Module purpose

Answer: **How good is the current RAG pipeline?**  
Show aggregate quality signals and recent experiment outcomes. No charts, no tuning.

---

## Screen E1 — Evaluation overview

### Purpose

Display overall quality snapshot from the latest completed run(s) and list recent evaluations.

### Wireframe

```text
┌────────────────────────────────────────────────────────────────┐
│ Evaluation                                                     │
│ Knowledge base [Policies KB ▾]     Dataset [kb-hr-fa-smoke ▾]  │
├────────────────────────────────────────────────────────────────┤
│ Overall quality (latest passed/failed run)                     │
│ Status: PASSED                                                 │
│                                                                │
│ Recall@K     0.84    MRR              0.71                     │
│ Groundedness 0.80    Citation Prec.   0.88                     │
│ Abstention P 1.00    e2e p95          1100 ms                  │
│                                                                │
│ Failing gates: —                                               │
├────────────────────────────────────────────────────────────────┤
│ Recent runs                                    [Open experiments]│
│ Run ID     Status   Dataset      Recall  Time                  │
│ run-a1…    passed   smoke@1.0.0  0.84    10:42 →               │
│ run-b2…    failed   smoke@1.0.0  0.61    Mon   →               │
└────────────────────────────────────────────────────────────────┘
```

### Components

`PageHeader`, `KnowledgeBaseSelect`, `DatasetSelect`, `MetricStatGrid`, `StatusChip`, `RecentRunsTable`, `FailingMetricsList`

### States

| State | UI |
| --- | --- |
| Loading | Stat skeletons + table skeleton |
| Success | Numbers from `metrics.json` + summary status |
| Empty | “No evaluation runs yet. Start an experiment.” + link to `/experiments/new` |
| Error | Unable to load artifacts / adapter unavailable |
| Partial | Some metrics `null` → show “—” (e.g. missing tokens) |

### API endpoints

| Action | Planned thin adapter | Backs onto |
| --- | --- | --- |
| List recent runs | `GET /api/v1/workspaces/{id}/evaluations/runs` | Feature 007 filesystem `experiments/*/summary.json` |
| Latest metrics | `GET /api/v1/workspaces/{id}/evaluations/runs/{run_id}/metrics` | `metrics.json` |
| KB filter | Existing knowledge list | Knowledge API |

Until adapters exist, screen may be **stubbed behind a feature flag** with empty state explaining “Evaluation API adapter pending.” Do not fake metrics.

### Loading

Initial page load waits for list; metric cards wait for selected/latest run.

### Errors

| Code / case | UI |
| --- | --- |
| Adapter 501/404 | Empty + “backend expose pending” |
| `forbidden` | Permission message |
| Corrupt metrics | Error row; do not render partial invented values |

### Empty states

- No runs for KB/dataset filters → clear empty + CTA to Experiments.
- Dataset selector empty → “No golden datasets registered.”

---

## Screen E2 — Run summary (lightweight)

### Purpose

Quick view of one run’s pass/fail and key metrics before opening full Experiments detail.

### Wireframe

```text
┌──────────────────────────────────────┐
│ Run run-a1…                  PASSED  │
│ Dataset kb-hr-fa-smoke@1.0.0         │
│ Config top_k=8 · prompt v1 · echo    │
│                                      │
│ Metrics (read-only grid)             │
│ [View full results] [Compare…]       │
└──────────────────────────────────────┘
```

### Components

`RunHeader`, `MetricStatGrid`, `ConfigSnapshotChips`, `LinkButton`

### States / API / Loading / Errors / Empty

Same data sources as E1; detail empty only if `run_id` unknown → 404 page with back link.

## Display rules

| Rule | Detail |
| --- | --- |
| Numbers | Fixed precision (e.g. 2 decimals) for rates |
| Nulls | Em dash; never coerce to `0` |
| Pass/fail | From `summary.status` (`passed` / `failed`) |
| No charts | Tables and metric tiles only |
| No optimization | No “improve score” CTAs |

## Module non-goals

- Dataset authoring UI
- Chart dashboards
- LLM-as-judge viewers
- Online A/B dashboards
