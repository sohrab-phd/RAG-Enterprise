import * as React from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { formatLatencyMs, formatMetric } from "@/features/evaluation/lib/format";
import type { EvaluationRunSummary } from "@/features/evaluation/types";
import { cn } from "@/lib/utils";

type MetricStatGridProps = {
  readonly run: EvaluationRunSummary | null;
  readonly loading?: boolean;
  readonly className?: string;
};

type MetricItem = {
  readonly label: string;
  readonly value: string;
};

function metricsFor(run: EvaluationRunSummary): MetricItem[] {
  return [
    { label: "Recall@K", value: formatMetric(run.recall_at_k) },
    { label: "MRR", value: formatMetric(run.mrr) },
    { label: "Groundedness", value: formatMetric(run.groundedness) },
    {
      label: "Citation precision",
      value: formatMetric(run.citation_precision_mean),
    },
    {
      label: "Citation accuracy",
      value: formatMetric(run.citation_accuracy),
    },
    {
      label: "Abstention precision",
      value: formatMetric(run.abstention_precision),
    },
    { label: "Retrieval latency", value: formatLatencyMs(run.retrieval_latency_mean_ms) },
    { label: "e2e p95", value: formatLatencyMs(run.e2e_p95_ms) },
  ];
}

export function MetricStatGrid({
  run,
  loading = false,
  className,
}: MetricStatGridProps): React.JSX.Element {
  if (loading) {
    return (
      <div
        className={cn("grid gap-3 sm:grid-cols-2 lg:grid-cols-4", className)}
        aria-busy="true"
        aria-label="Loading metrics"
      >
        {Array.from({ length: 8 }).map((_, index) => (
          <Skeleton key={index} className="h-20 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (!run) {
    return (
      <p className={cn("text-sm text-muted-foreground", className)}>
        Metrics appear after at least one completed evaluation run.
      </p>
    );
  }

  return (
    <div
      className={cn("grid gap-3 sm:grid-cols-2 lg:grid-cols-4", className)}
      aria-label="Quality metrics"
    >
      {metricsFor(run).map((item) => (
        <div key={item.label} className="rounded-lg border border-border bg-card px-3 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {item.label}
          </p>
          <p className="mt-1 font-mono text-2xl tabular-nums text-foreground">{item.value}</p>
        </div>
      ))}
    </div>
  );
}
