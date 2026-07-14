# Offline evaluation framework (Feature 007)

> **Status:** Implemented  
> **Spec:** [007 Evaluation Framework](../../specs/007-evaluation-framework/README.md)

## Purpose

Measure retrieval and RAG generation quality with a versioned golden dataset and
reproducible offline experiments. No UI, dashboards, charts, or optimization.

## Pipeline

```text
Golden Dataset (JSONL + manifest)
  → ExperimentConfig (pinned RAG settings)
  → ExperimentRunner (retrieve + generate per question)
  → Metrics (Recall@K, MRR, citations, abstention, latency, tokens)
  → Filesystem artifacts under experiments/{run_id}/
```

Evaluation calls Feature 005 retrieval and Feature 006 generation as black boxes.

## Package

```text
backend/src/rag_enterprise/evaluation/
  dataset/          # load + validate versioned JSONL datasets
  metrics/          # deterministic scores (no LLM judge)
  runner/           # experiment execution
  storage/          # filesystem persistence
  models/           # config, outcomes, metric report shapes
  service.py        # EvaluationService facade
  exceptions.py
```

## Dataset layout

```text
{dataset_dir}/
  manifest.json
  dataset.jsonl
```

Malformed rows fail the entire load (strict v1). Published dataset versions are
immutable; edits require a new version.

## Experiment artifacts

```text
{storage_root}/
  experiments/
    {experiment_id}/
      config.json
      results.jsonl
      metrics.json
      summary.json
```

No database tables in v1.

Startup configuration validation ensures `EVALUATION_STORAGE_ROOT` exists or is
created before the API accepts traffic. See [CONFIGURATION.md](CONFIGURATION.md).

## Metrics (v1)

| Layer | Metrics |
| --- | --- |
| Retrieval | Recall@K (any-hit), MRR |
| Generation | Groundedness (citation-based), Citation Precision (mean), Citation Accuracy, Abstention Precision (+ Recall diagnostic) |
| Operational | e2e / retrieval / generation latency (p50, p95, mean), token totals when reported |

All scoring is deterministic: chunk-id overlap and binary status checks only.

RC1.3 reuses these metrics (and a one-question offline experiment) in the golden-path
E2E scenario. See [End-to-End Happy Path](E2E_HAPPY_PATH.md).

## Usage

```python
from pathlib import Path
from rag_enterprise.evaluation import EvaluationService

service = EvaluationService(
    retrieval_service=retrieval,
    generation_service=generation,
    storage_root=Path("./eval-artifacts"),
)
config = service.create_config(
    name="smoke-topk8-v1",
    organization_id=org_id,
    workspace_id=workspace_id,
    user_id=user_id,
    knowledge_base_id=kb_id,
    dataset_id="kb-hr-fa-smoke",
    dataset_version="1.0.0",
    dataset_path=str(dataset_dir),
    top_k=8,
)
summary = await service.run(config)
# summary.status → passed | failed
# summary.artifact_dir → .../experiments/{id}
```

## Non-goals

- Dashboard / charts / frontend
- Automatic hyperparameter search
- LLM-as-judge
- Online A/B serving
- Production config mutation
