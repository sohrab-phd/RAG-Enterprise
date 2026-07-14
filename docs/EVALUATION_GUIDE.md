# Evaluation Guide

> **Purpose:** How to measure RAG quality with Feature 007 in Version 1.0.0.  
> **Release:** 1.0.0  
> **Authority:** Dataset and metric contracts live in the spec and backend docs.

## Purpose

Explain how offline evaluation fits the platform and where to find schemas, metrics,
and the official demo golden set—without restating Feature 007 prose.

## Audience

Quality engineers, AI engineers, and operators running reproducible experiments.

## What evaluation is (and is not)

Evaluation **measures** retrieval and generation against a versioned golden dataset.
It does not optimize ranking, prompts, or the chatbot UI.

**Version 1.0.0:** experiment **execution remains offline** (filesystem datasets +
`EvaluationService` runner). There is no online/continuous evaluation loop and no
experiment authoring UI (those are **Version 2**).

Pipeline sketch:

```text
Golden dataset → ExperimentConfig → Runner (retrieve + generate) → Metrics → Artifacts
```

## Offline evaluation engine

Backend module: [EVALUATION_FRAMEWORK.md](backend/EVALUATION_FRAMEWORK.md).

- Loads `manifest.json` + `dataset.jsonl`
- Calls Feature 005 retrieval and Feature 006 generation as black boxes
- Writes run artifacts under `EVALUATION_STORAGE_ROOT` / `experiments/{run_id}/`

## Supported metrics (Version 1.0.0)

| Layer | Metrics |
| --- | --- |
| Retrieval | Recall@K (any-hit), MRR |
| Generation | Groundedness, Citation Precision, Citation Accuracy, Abstention Precision (+ Recall diagnostic) |
| Operational | e2e / retrieval / generation latency (p50, p95, mean), token totals when reported |

All scoring is deterministic (chunk-id overlap and status checks). Details:
[METRICS.md](../specs/007-evaluation-framework/METRICS.md).

## Evaluation dashboard

The operator console **Evaluation** module (Feature 008) reads Feature 007 filesystem
adapters to list runs, show summaries, and open run detail. It does **not** execute
experiments itself in Version 1.0.0.

See [frontend/README.md](../frontend/README.md).

## Authoritative documents

| Need | Link |
| --- | --- |
| Spec overview | [specs/007-evaluation-framework](../specs/007-evaluation-framework/README.md) |
| Dataset schema | [DATASET.md](../specs/007-evaluation-framework/DATASET.md) |
| Metrics | [METRICS.md](../specs/007-evaluation-framework/METRICS.md) |
| Experiments | [EXPERIMENTS.md](../specs/007-evaluation-framework/EXPERIMENTS.md) |
| Backend usage | [EVALUATION_FRAMEWORK.md](backend/EVALUATION_FRAMEWORK.md) |

## Official demo golden set

1. Follow [Demo Guide](DEMO_GUIDE.md) (Create → Upload → Process & Index → Publish → Chat).
2. Prepare Feature 007 files from `demo/evaluation/` (copy `evaluation.jsonl` →
   `dataset.jsonl` as described in [demo/README.md](../demo/README.md)).
3. Bind live `knowledge_base_id` / citation ids before scoring (see
   [demo/evaluation/ID_MAP.md](../demo/evaluation/ID_MAP.md)).
4. Run the offline engine, then inspect results in the Evaluation Dashboard.

## Automated smoke

CI-oriented single-question path: [E2E Happy Path](backend/E2E_HAPPY_PATH.md).

## Related documents

- [Feature Map](FEATURE_MAP.md)
- [Demo Guide](DEMO_GUIDE.md)
- [Roadmap](ROADMAP.md) (Version 2: experiment authoring)
- [Documentation index](README.md)
