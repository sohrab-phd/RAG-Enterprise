# Acceptance Criteria

> **Spec:** 007-evaluation-framework  
> **Authority:** Given/When/Then scenarios for the evaluation framework

## AC-01: Load golden dataset

**Given** a published dataset version `kb-hr-fa-smoke@1.0.0` with valid JSONL records  
**When** an experiment references that dataset version  
**Then** the runner loads all questions  
**And** rejects the run if required fields (`id`, `question`, `expected_citations`, `difficulty`, `language`, `tags`, `knowledge_base_id`) are missing

## AC-02: Run all questions

**Given** an experiment config with embedding model, chunk size, overlap, top-K, prompt version, LLM, and dataset version  
**When** the experiment executes  
**Then** every question produces a per-question outcome record  
**And** the experiment status moves `defined` → `running` → `passed` or `failed`

## AC-03: Retrieval metrics computed

**Given** completed retrieval results for answerable questions  
**When** aggregation runs  
**Then** `Recall@K` and `MRR` are present in `metrics.json`  
**And** `K` equals the experiment `top_k`

## AC-04: Generation metrics computed

**Given** generation results for the same experiment  
**When** aggregation runs  
**Then** groundedness, citation precision (mean), and abstention precision are present  
**And** abstention questions do not inflate groundedness denominators

## AC-05: Latency and tokens recorded

**Given** a finished experiment  
**When** inspecting per-question outcomes  
**Then** `e2e_latency_ms` is stored for each successful question  
**And** token fields are stored when the LLM provider reports them, else `null`

## AC-06: Persist experiment results

**Given** a finished experiment  
**When** persistence completes  
**Then** `config.json`, `results.jsonl`, and `metrics.json` exist under the experiment artifact path  
**And** the frozen config matches the values used for the run

## AC-07: Pass/fail against thresholds

**Given** thresholds `recall_at_k ≥ 0.70` and `groundedness ≥ 0.70`  
**And** the run achieves recall 0.80 and groundedness 0.60  
**When** gates are evaluated  
**Then** experiment status is `failed`  
**And** `summary.json` lists `groundedness` as a failing metric

## AC-08: Abstention precision

**Given** five questions with `expect_abstention = true`  
**And** the system abstains on those five and also abstains incorrectly on one answerable question  
**When** metrics are computed  
**Then** Abstention Precision = 5/6  
**And** Abstention Recall = 5/5

## AC-09: Reproducibility fingerprint

**Given** the same dataset version and identical experiment config  
**When** two runs execute against an unchanged indexed corpus and deterministic providers  
**Then** retrieval hit sets and metric aggregates match within documented float tolerance  
**And** each run still receives a distinct `experiment_id`

## AC-10: No production mutation

**Given** a running evaluation  
**When** the runner finishes  
**Then** no production prompt, embedding model assignment, or retrieval default is modified  
**And** no chat UI or dashboard artifact is created

## AC-11: Multilingual labels

**Given** dataset questions tagged `language = fa` and `language = en`  
**When** the report is written  
**Then** per-language breakdown counts are included as diagnostics in `metrics.json` (optional section `by_language`)  
**And** overall gates still use the full applicable set

## AC-12: Invalid dataset row skipped

**Given** one JSONL row missing `difficulty`  
**When** the dataset is loaded  
**Then** that row is rejected with a validation error listing the question `id` if present  
**And** the experiment does not start until the dataset is fixed (strict v1)
