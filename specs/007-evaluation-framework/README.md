# Evaluation Framework

> **Spec ID:** 007  
> **Status:** Implemented  
> **Goal:** Measure retrieval and RAG generation quality with a versioned golden dataset and reproducible experiments.  
> **Scope:** Offline evaluation framework only — no UI, dashboards, optimization, or chatbot changes.

## Purpose

Phase 6 answers: **how good is the current RAG pipeline?**  
It does not improve ranking, prompts, or generation. It measures them.

```text
Golden Dataset (versioned)
  → Experiment (pinned RAG config)
  → Run all questions
  → Compute metrics
  → Persist results
```

Evaluation is owned by the **Quality and Evaluation** bounded context and scopes to a
`KnowledgeBase` (and effective retrieval/generation settings). See
[Domain Model — Evaluation](../../docs/domain/DOMAIN_MODEL.md) and
[Entity Lifecycle — Evaluation](../../docs/domain/ENTITY_LIFECYCLE.md).

## Goals

| Goal | Description |
| --- | --- |
| Reproducibility | Same dataset + experiment config → comparable runs |
| Coverage | Measure retrieval and generation separately, then as an end-to-end turn |
| Simplicity | Offline runner; JSON datasets; stored metric summaries |
| Safety | Synthetic or approved fixtures only — no uncontrolled production PII |

## Non-goals

| Out of scope | Reason |
| --- | --- |
| UI / charts / dashboards | Measurement only |
| Automatic hyperparameter search | No optimization |
| Public leaderboards / benchmarking contests | Internal measurement |
| Chatbot UX changes | Specs 005–006 unchanged |
| Online A/B serving | Offline experiments first |
| Human-in-the-loop labeling UI | Dataset authored as files |

## Spec map

| Document | Contents |
| --- | --- |
| [DATASET.md](DATASET.md) | Golden dataset schema and versioning |
| [METRICS.md](METRICS.md) | Retrieval, generation, latency, and cost metrics |
| [EXPERIMENTS.md](EXPERIMENTS.md) | Experiment config, execution, persistence |
| [ACCEPTANCE.md](ACCEPTANCE.md) | Given/When/Then acceptance scenarios |

## Pipeline position

```text
001 Knowledge → 002 Process → 003 Chunk → 004 Embed → 005 Retrieve → 006 Generate
                                                                         ↑
                                                              007 Evaluation measures this
```

Evaluation **calls** retrieval and generation as black boxes. It does not reimplement them.

## Ownership and access

| Concern | Rule |
| --- | --- |
| Aggregate | Organization-owned `Evaluation` / experiment run |
| Permission | `organization:evaluation:manage` to define and run |
| Scope | One knowledge base per experiment (v1) |
| Artifacts | Dataset + results in object storage; run metadata in PostgreSQL (later) |

## Package

```text
backend/src/rag_enterprise/evaluation/
  dataset/
  metrics/
  runner/
  storage/
  models/
  service.py
```

See [EVALUATION_FRAMEWORK.md](../../docs/backend/EVALUATION_FRAMEWORK.md).

## Related documents

- [006 RAG Generation](../006-rag-generation/SPEC.md)
- [005 Retrieval](../005-retrieval/SPEC.md)
- [004 Embeddings](../004-embeddings/SPEC.md)
- [Storage Strategy — evaluation artifacts](../../docs/data/STORAGE_STRATEGY.md)
- [AI Engineering Rules — evaluation](../../.cursor/rules/ai-engineering.md)
