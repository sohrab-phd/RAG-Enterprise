import { apiRequest, workspacePath } from "@/lib/api/client";
import type {
  EvaluationDatasetList,
  EvaluationRunDetail,
  EvaluationRunList,
} from "@/features/evaluation/types";

export type ListRunsParams = {
  readonly knowledgeBaseId?: string | null;
  readonly datasetId?: string | null;
  readonly limit?: number;
  readonly signal?: AbortSignal;
};

export function listEvaluationRuns(params: ListRunsParams = {}): Promise<EvaluationRunList> {
  const search = new URLSearchParams();
  if (params.knowledgeBaseId) {
    search.set("knowledge_base_id", params.knowledgeBaseId);
  }
  if (params.datasetId) {
    search.set("dataset_id", params.datasetId);
  }
  if (params.limit != null) {
    search.set("limit", String(params.limit));
  }
  const query = search.toString();
  return apiRequest(workspacePath(`/evaluations/runs${query ? `?${query}` : ""}`), {
    signal: params.signal,
  });
}

export function getEvaluationRun(
  runId: string,
  signal?: AbortSignal,
): Promise<EvaluationRunDetail> {
  return apiRequest(workspacePath(`/evaluations/runs/${runId}`), { signal });
}

export function listEvaluationDatasets(signal?: AbortSignal): Promise<EvaluationDatasetList> {
  return apiRequest(workspacePath("/evaluations/datasets"), { signal });
}
