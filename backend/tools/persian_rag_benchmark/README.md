# Persian RAG Diagnostics & Benchmark Framework

Developer-only suite for **Version 1.0.0** Persian RAG measurement.

Does **not** modify production code or APIs. Calls production services via `AppContainer`.

## Trust model (RC1.7)

| Trust | Meaning |
| --- | --- |
| **Measured** | Taken from production retrieve/generate/embed outputs with standard formulas |
| **Derived** | Deterministic transform of measured fields (e.g. Exact Match after digit normalize) |
| **Estimated** | Incomplete / sampled measurement |
| **Heuristic** | Proxy score — never for acceptance |

**Circular evaluation removed:** auto-generated corpus probes are labeled
`gold_provenance=auto_corpus_probe` and `eligible_for_measured_retrieval=false`.
**Measured** Hit@k / Recall@k / Precision@k / MRR require curated external gold
(`--dataset-path`).

**Baseline vs Robustness never mixed** in aggregates or subsystem scores.

**No “Version 1 Ready” heuristic.** HTML starts with the **Benchmark Trust Report**.

## Run

From `backend/`:

```powershell
# Measured path (recommended) — curated demo gold bound to live chunks by passage
uv run python -m tools.persian_rag_benchmark `
  --knowledge-base-id <ACTIVE_KB_UUID> `
  --dataset-path ../demo/evaluation

# Probes only (NOT Measured for retrieval; diagnostics/heuristics)
uv run python -m tools.persian_rag_benchmark `
  --knowledge-base-id <ACTIVE_KB_UUID> `
  --enable-auto-corpus-probes
```

Artifacts:

```text
benchmark-artifacts/persian-rag/<run-id>/
  dataset/
  diagnostics.json
  diagnostics.csv
  diagnostics.html      # Trust Report is page 1
  trust_report.json
```

## IR formulas (Measured)

- **Hit@k** = 1 if expected chunk ∈ top-k else 0
- **Recall@k** = |expected ∩ top-k| / |expected|
- **Precision@k** = |expected ∩ top-k| / **k** (always k)
- **MRR** = 1/rank of first expected chunk (0 if missing)

## Heuristic metric names

| Old | New |
| --- | --- |
| Semantic Similarity | Lexical Overlap (Heuristic) |
| Fluency | Heuristic Fluency Estimate |
| Entity Accuracy | Entity Match Estimate |
| Procedure Accuracy | Procedure Match Estimate |

## RCA

Each failure lists `likely_root_cause`, `confidence` ∈ [0,1], and `evidence[]` —
not hard deterministic labels.

## Tests

```powershell
cd backend
uv run pytest tests/tools/persian_rag_benchmark -q
```
