# Evaluation Metrics

> **Spec:** 007-evaluation-framework  
> **Authority:** Metric definitions for offline RAG evaluation

## 1. Principles

| Principle | Rule |
| --- | --- |
| Separate layers | Report **retrieval** and **generation** metrics distinctly |
| Fixed K | Use the experiment’s `top_k` for Recall@K / citation checks |
| Deterministic scoring | Prefer exact id matches and simple binary checks over model judges in v1 |
| Persist everything | Per-question raw outcomes + dataset-level aggregates |

v1 does **not** require an LLM-as-judge. Groundedness uses citation overlap against expected citations (and optional lexical overlap). Future judge models need a separate revision.

---

## 2. Retrieval metrics

Computed from Feature 005 outputs vs `expected_citations` / golden chunk ids.

### 2.1 Recall@K

**Definition:** Fraction of questions where **at least one** expected citation chunk appears in the top-K retrieved results.

```text
Recall@K = (# questions with ≥1 expected chunk_id in retrieved top-K) / (# questions)
```

For multi-evidence questions, optional stretch metric (v1.1):  
`Recall_all@K` = fraction where **all** expected chunk ids appear in top-K.  
**v1 reports Recall@K (any-hit)** only.

### 2.2 MRR (Mean Reciprocal Rank)

For each question, find the **best (lowest) rank** among expected chunk ids in the retrieved list (1-based).  
If none found, reciprocal rank = 0.

```text
RR_i = 1 / rank_of_first_expected_hit   (or 0)
MRR = average(RR_i) over questions
```

Abstention-labeled questions (`expect_abstention = true`) are **excluded** from retrieval metrics unless the experiment opts in via `include_abstain_in_retrieval = true` (default **false**).

---

## 3. Generation metrics

Computed from Feature 006 `GenerationResult` vs golden fields.

### 3.1 Groundedness

**v1 definition (citation-based):**

A completed answer is **grounded** if:

1. `status = completed`, and  
2. At least one returned citation `chunk_id` is in the expected citation set **or** in the retrieved set for that turn, and  
3. Every returned citation `chunk_id` was present in the retrieval set (no fabricated ids).

```text
Groundedness = (# grounded completed answers) / (# questions where expect_abstention = false)
```

Questions expecting abstention are excluded from this denominator.

Optional diagnostic (logged, not gating): token-overlap F1 between `answer` and `expected_answer` after whitespace normalize. Not used for pass/fail in v1.

### 3.2 Citation Accuracy

Among questions with `expect_abstention = false` and `status = completed`:

```text
Citation Precision = |cited_chunk_ids ∩ expected_chunk_ids| / |cited_chunk_ids|
Citation Recall    = |cited_chunk_ids ∩ expected_chunk_ids| / |expected_chunk_ids|
Citation Accuracy  = fraction of questions where Citation Precision ≥ 1.0
                     (every cited chunk is expected) AND Citation Recall ≥ 1.0
                     (all expected chunks were cited)
                     — if expected set empty, treat question as N/A
```

**v1 primary score:** mean Citation Precision across applicable questions.  
**v1 secondary:** Citation Accuracy (strict all-or-nothing) as a harder bar.

If `expected_citations` is empty and abstention is not expected, the question is **invalid** dataset data and is skipped with a warning.

### 3.3 Abstention Precision

Among questions where the system abstained (`status = abstained`):

```text
Abstention Precision = (# abstentions where expect_abstention = true)
                     / (# abstentions)
```

Optional companion (logged):

```text
Abstention Recall = (# abstentions where expect_abstention = true)
                  / (# questions where expect_abstention = true)
```

v1 gates on **Abstention Precision** (avoid abstaining incorrectly) and reports Recall as diagnostic.

---

## 4. Operational metrics

Measured per question and aggregated.

### 4.1 Latency

| Metric | Definition |
| --- | --- |
| `retrieval_latency_ms` | Time inside retrieval call |
| `generation_latency_ms` | Time inside generation call (includes retrieve if measured end-to-end) |
| `e2e_latency_ms` | Wall clock for full eval turn |

Aggregates: **p50**, **p95**, mean.

### 4.2 Token usage

| Metric | Definition |
| --- | --- |
| `prompt_tokens` | Input tokens when provider reports them; else `null` |
| `completion_tokens` | Output tokens when provider reports them; else `null` |
| `total_tokens` | Sum when both known |

If the provider (e.g. echo mode) does not report tokens, store `null` and exclude from averages (count as missing, not zero).

---

## 5. Aggregate report shape

```json
{
  "dataset_id": "kb-hr-fa-smoke",
  "dataset_version": "1.0.0",
  "experiment_id": "...",
  "metrics": {
    "retrieval": {
      "recall_at_k": 0.84,
      "mrr": 0.71,
      "k": 8,
      "n": 20
    },
    "generation": {
      "groundedness": 0.80,
      "citation_precision_mean": 0.88,
      "citation_accuracy": 0.72,
      "abstention_precision": 1.0,
      "abstention_recall": 0.90,
      "n_answerable": 20,
      "n_abstain_cases": 5
    },
    "latency_ms": {
      "e2e_p50": 420,
      "e2e_p95": 1100,
      "e2e_mean": 510
    },
    "tokens": {
      "total_mean": 1800,
      "missing_count": 0
    }
  }
}
```

## 6. Pass / fail thresholds (defaults)

Thresholds are **experiment configuration**, not hard-coded forever. Suggested smoke defaults:

| Metric | Suggested smoke threshold |
| --- | --- |
| Recall@K | ≥ 0.70 |
| MRR | ≥ 0.50 |
| Groundedness | ≥ 0.70 |
| Citation Precision (mean) | ≥ 0.70 |
| Abstention Precision | ≥ 0.80 |
| e2e p95 latency | Informative only in v1 (no gate) |

A run is `passed` if all configured gates pass; else `failed` (matches Evaluation lifecycle).

## 7. Out of scope

- BLEU/ROUGE as primary quality scores
- LLM-as-judge in v1
- Fairness / bias suites
- Cost billing dashboards
