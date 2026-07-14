export const evaluationKeys = {
  all: ["evaluation"] as const,
  runs: (filters: { readonly knowledgeBaseId: string | null; readonly datasetId: string | null }) =>
    [...evaluationKeys.all, "runs", filters] as const,
  run: (runId: string) => [...evaluationKeys.all, "run", runId] as const,
  datasets: () => [...evaluationKeys.all, "datasets"] as const,
};
