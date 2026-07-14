import * as React from "react";
import { Link } from "react-router-dom";

import { Skeleton } from "@/components/ui/skeleton";
import { formatMetric, formatLatencyMs, shortRunId } from "@/features/evaluation/lib/format";
import type { EvaluationRunSummary } from "@/features/evaluation/types";
import { EmptyState } from "@/features/knowledge/components/empty-state";
import { StatusChip } from "@/features/knowledge/components/status-chip";
import { formatRelativeTime } from "@/features/knowledge/lib/format";
import { cn } from "@/lib/utils";

type RecentRunsTableProps = {
  readonly runs: readonly EvaluationRunSummary[];
  readonly loading?: boolean;
  readonly activeRunId?: string | null;
  readonly onNewExperiment?: () => void;
  readonly className?: string;
};

export function RecentRunsTable({
  runs,
  loading = false,
  activeRunId = null,
  onNewExperiment,
  className,
}: RecentRunsTableProps): React.JSX.Element {
  if (loading) {
    return (
      <div className={cn("space-y-2", className)} aria-busy="true">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <EmptyState
        title="No evaluation runs yet"
        description="Start an experiment to measure retrieval and generation quality."
        actionLabel={onNewExperiment ? "New experiment" : undefined}
        onAction={onNewExperiment}
        className={className}
      />
    );
  }

  return (
    <div className={cn("overflow-x-auto rounded-lg border border-border", className)}>
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead className="border-b border-border bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-3 py-2 font-medium">Run</th>
            <th className="px-3 py-2 font-medium">Status</th>
            <th className="px-3 py-2 font-medium">Dataset</th>
            <th className="px-3 py-2 font-medium">Recall@K</th>
            <th className="px-3 py-2 font-medium">Groundedness</th>
            <th className="px-3 py-2 font-medium">e2e p95</th>
            <th className="px-3 py-2 font-medium">When</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => {
            const active = run.run_id === activeRunId;
            return (
              <tr
                key={run.run_id}
                className={cn(
                  "border-b border-border last:border-b-0 hover:bg-muted/30",
                  active && "bg-muted/50",
                )}
              >
                <td className="px-3 py-2">
                  <Link
                    to={`/evaluation/runs/${run.run_id}`}
                    className="font-medium text-foreground underline-offset-2 hover:underline"
                  >
                    <span className="block truncate">{run.name}</span>
                    <span className="block font-mono text-xs text-muted-foreground">
                      {shortRunId(run.run_id)}
                    </span>
                  </Link>
                </td>
                <td className="px-3 py-2">
                  <StatusChip status={run.status} />
                </td>
                <td className="px-3 py-2 text-muted-foreground">
                  {run.dataset_id}@{run.dataset_version}
                </td>
                <td className="px-3 py-2 font-mono tabular-nums">
                  {formatMetric(run.recall_at_k)}
                </td>
                <td className="px-3 py-2 font-mono tabular-nums">
                  {formatMetric(run.groundedness)}
                </td>
                <td className="px-3 py-2 font-mono tabular-nums">
                  {formatLatencyMs(run.e2e_p95_ms)}
                </td>
                <td className="px-3 py-2 text-muted-foreground">
                  {run.created_at ? formatRelativeTime(run.created_at) : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
