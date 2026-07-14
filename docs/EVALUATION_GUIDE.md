# Evaluation Guide

> **Purpose:** How to measure RAG quality with Feature 007 in Version 1.  
> **Authority:** Dataset and metric contracts live in the spec and backend docs.

## Purpose

Explain how offline evaluation fits the platform and where to find schemas, metrics,
and the official demo golden set—without restating Feature 007 prose.

## Audience

Quality engineers, AI engineers, and operators running reproducible experiments.

## What evaluation is (and is not)

Evaluation **measures** retrieval and generation against a versioned golden dataset.
It does not optimize ranking, prompts, or the chatbot UI.

Pipeline sketch:

```text
Golden dataset → ExperimentConfig → Runner (retrieve + generate) → Metrics → Artifacts
```

## Authoritative documents

| Need | Link |
| --- | --- |
| Spec overview | [specs/007-evaluation-framework](../specs/007-evaluation-framework/README.md) |
| Dataset schema | [DATASET.md](../specs/007-evaluation-framework/DATASET.md) |
| Metrics | [METRICS.md](../specs/007-evaluation-framework/METRICS.md) |
| Experiments | [EXPERIMENTS.md](../specs/007-evaluation-framework/EXPERIMENTS.md) |
| Backend usage | [EVALUATION_FRAMEWORK.md](backend/EVALUATION_FRAMEWORK.md) |

## Official demo golden set

Use the RC1.4 corpus and questions:

1. Follow [Demo Guide](DEMO_GUIDE.md) to import and index `demo/knowledge/`.
2. Prepare Feature 007 files from `demo/evaluation/` (copy `evaluation.jsonl` →
   `dataset.jsonl` as described in [demo/README.md](../demo/README.md)).
3. Bind live `knowledge_base_id` / citation ids before scoring (see
   [demo/evaluation/ID_MAP.md](../demo/evaluation/ID_MAP.md)).

## Automated smoke

CI-oriented single-question path: [E2E Happy Path](backend/E2E_HAPPY_PATH.md).

## Operator console

The frontend Evaluation module reads Feature 007 filesystem adapters—see
[frontend/README.md](../frontend/README.md).

## Related documents

- [Feature Map](FEATURE_MAP.md)
- [Demo Guide](DEMO_GUIDE.md)
- [Documentation index](README.md)
