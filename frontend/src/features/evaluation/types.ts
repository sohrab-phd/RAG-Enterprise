/** Evaluation run DTOs mapped from Feature 007 read adapters. */

export type EvaluationRunSummary = {
  readonly run_id: string;
  readonly name: string;
  readonly status: string;
  readonly knowledge_base_id: string;
  readonly dataset_id: string;
  readonly dataset_version: string;
  readonly created_at: string | null;
  readonly top_k: number;
  readonly prompt_version: string;
  readonly llm: string;
  readonly failing_metrics: readonly string[];
  readonly question_count: number;
  readonly error_count: number;
  readonly recall_at_k: number | null;
  readonly mrr: number | null;
  readonly groundedness: number | null;
  readonly citation_accuracy: number | null;
  readonly citation_precision_mean: number | null;
  readonly abstention_precision: number | null;
  readonly retrieval_latency_mean_ms: number | null;
  readonly e2e_p95_ms: number | null;
  readonly e2e_p50_ms: number | null;
  readonly e2e_mean_ms: number | null;
};

export type EvaluationRunList = {
  readonly items: readonly EvaluationRunSummary[];
};

export type EvaluationRunDetail = {
  readonly run_id: string;
  readonly config: Readonly<Record<string, unknown>>;
  readonly summary: Readonly<Record<string, unknown>>;
  readonly metrics: Readonly<Record<string, unknown>>;
};

export type EvaluationDatasetList = {
  readonly items: readonly string[];
};
