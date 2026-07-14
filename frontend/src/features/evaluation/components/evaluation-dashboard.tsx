import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  getEvaluationRun,
  listEvaluationDatasets,
  listEvaluationRuns,
} from "@/features/evaluation/api";
import { MetricStatGrid } from "@/features/evaluation/components/metric-stat-grid";
import { RecentRunsTable } from "@/features/evaluation/components/recent-runs-table";
import { RunDetailView } from "@/features/evaluation/components/run-detail-view";
import { TrendCharts } from "@/features/evaluation/components/trend-charts";
import { latestCompletedRun } from "@/features/evaluation/lib/format";
import { evaluationKeys } from "@/features/evaluation/query-keys";
import { listKnowledgeBases } from "@/features/knowledge/api";
import { ErrorState } from "@/features/knowledge/components/error-state";
import { StatusChip } from "@/features/knowledge/components/status-chip";
import { knowledgeKeys } from "@/features/knowledge/query-keys";
import { isApiError } from "@/lib/api/types";

const ALL = "__all__";

export function EvaluationDashboard(): React.JSX.Element {
  const { runId: routeRunId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const knowledgeBaseId = searchParams.get("kbId");
  const datasetId = searchParams.get("datasetId");

  const kbQuery = useQuery({
    queryKey: knowledgeKeys.baseList({ page: 1, pageSize: 100 }),
    queryFn: ({ signal }) => listKnowledgeBases({ page: 1, pageSize: 100, signal }),
  });

  const datasetsQuery = useQuery({
    queryKey: evaluationKeys.datasets(),
    queryFn: ({ signal }) => listEvaluationDatasets(signal),
  });

  const runsQuery = useQuery({
    queryKey: evaluationKeys.runs({
      knowledgeBaseId,
      datasetId,
    }),
    queryFn: ({ signal }) =>
      listEvaluationRuns({
        knowledgeBaseId,
        datasetId,
        limit: 50,
        signal,
      }),
  });

  const selectedRunId =
    routeRunId ?? latestCompletedRun(runsQuery.data?.items ?? [])?.run_id ?? null;

  const detailQuery = useQuery({
    queryKey: evaluationKeys.run(selectedRunId ?? "none"),
    queryFn: ({ signal }) => {
      if (!selectedRunId) {
        throw new Error("run id required");
      }
      return getEvaluationRun(selectedRunId, signal);
    },
    enabled: Boolean(selectedRunId),
  });

  const runs = runsQuery.data?.items ?? [];
  const overviewRun = runs.find((run) => run.run_id === selectedRunId) ?? latestCompletedRun(runs);

  const setFilter = (key: "kbId" | "datasetId", value: string | null): void => {
    const next = new URLSearchParams(searchParams);
    if (!value) {
      next.delete(key);
    } else {
      next.set(key, value);
    }
    setSearchParams(next, { replace: true });
  };

  const listError = runsQuery.error;
  const adapterPending =
    isApiError(listError) && (listError.status === 404 || listError.status === 501);

  return (
    <section className="space-y-6" aria-label="Evaluation dashboard">
      <PageHeader
        title="Evaluation"
        description="Offline quality snapshot from Feature 007 experiment artifacts. Measurement only—no optimization."
        actions={
          <Button asChild variant="outline">
            <Link to="/experiments">Open experiments</Link>
          </Button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div className="space-y-1.5">
          <Label htmlFor="eval-kb">Knowledge base</Label>
          <Select
            value={knowledgeBaseId ?? ALL}
            onValueChange={(value) => setFilter("kbId", value === ALL ? null : value)}
            disabled={kbQuery.isLoading}
          >
            <SelectTrigger id="eval-kb" aria-label="Knowledge base filter">
              <SelectValue placeholder="All knowledge bases" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All knowledge bases</SelectItem>
              {(kbQuery.data?.items ?? []).map((kb) => (
                <SelectItem key={kb.id} value={kb.id}>
                  {kb.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="eval-dataset">Dataset</Label>
          <Select
            value={datasetId ?? ALL}
            onValueChange={(value) => setFilter("datasetId", value === ALL ? null : value)}
            disabled={datasetsQuery.isLoading}
          >
            <SelectTrigger id="eval-dataset" aria-label="Dataset filter">
              <SelectValue placeholder="All datasets" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All datasets</SelectItem>
              {(datasetsQuery.data?.items ?? []).map((id) => (
                <SelectItem key={id} value={id}>
                  {id}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {!datasetsQuery.isLoading && (datasetsQuery.data?.items.length ?? 0) === 0 ? (
            <p className="text-xs text-muted-foreground">
              No golden datasets registered in stored runs.
            </p>
          ) : null}
        </div>
      </div>

      {runsQuery.isError ? (
        <ErrorState
          title={
            adapterPending ? "Evaluation API adapter unavailable" : "Unable to load evaluation runs"
          }
          error={listError}
          onRetry={() => void runsQuery.refetch()}
        />
      ) : null}

      {!runsQuery.isError ? (
        <>
          <section className="space-y-3 rounded-lg border border-border bg-card p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-sm font-semibold">Overall quality</h2>
                <p className="text-xs text-muted-foreground">
                  Latest completed run in the current filters
                </p>
              </div>
              {overviewRun ? <StatusChip status={overviewRun.status} /> : null}
            </div>
            <MetricStatGrid run={overviewRun} loading={runsQuery.isLoading} />
            {overviewRun ? (
              <div className="space-y-1 text-sm">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Failing gates
                </p>
                {overviewRun.failing_metrics.length === 0 ? (
                  <p className="text-muted-foreground">—</p>
                ) : (
                  <ul className="flex flex-wrap gap-1">
                    {overviewRun.failing_metrics.map((metric) => (
                      <li
                        key={metric}
                        className="rounded bg-destructive/10 px-2 py-0.5 text-xs text-destructive"
                      >
                        {metric}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : null}
          </section>

          {runs.length > 0 ? <TrendCharts runs={runs} /> : null}

          <section className="space-y-3">
            <div className="flex items-end justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold">Recent runs</h2>
                <p className="text-xs text-muted-foreground">
                  Filesystem experiment summaries for this workspace
                </p>
              </div>
              <Button asChild variant="ghost" size="sm">
                <Link to="/experiments">Browse all</Link>
              </Button>
            </div>
            <RecentRunsTable
              runs={runs}
              loading={runsQuery.isLoading}
              activeRunId={selectedRunId}
              onNewExperiment={() => navigate("/experiments/new")}
            />
          </section>

          <section className="space-y-3">
            <h2 className="text-sm font-semibold">Run details</h2>
            {detailQuery.isError ? (
              <ErrorState
                title="Unable to load run details"
                error={detailQuery.error}
                onRetry={() => void detailQuery.refetch()}
              />
            ) : (
              <RunDetailView
                summary={overviewRun}
                detail={detailQuery.data ?? null}
                loading={Boolean(selectedRunId) && detailQuery.isLoading}
              />
            )}
          </section>
        </>
      ) : null}
    </section>
  );
}
