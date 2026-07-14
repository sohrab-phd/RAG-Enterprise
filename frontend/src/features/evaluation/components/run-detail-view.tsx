import * as React from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { MetricStatGrid } from "@/features/evaluation/components/metric-stat-grid";
import { formatLatencyMs, formatMetric, shortRunId } from "@/features/evaluation/lib/format";
import type { EvaluationRunDetail, EvaluationRunSummary } from "@/features/evaluation/types";
import { StatusChip } from "@/features/knowledge/components/status-chip";
import { Skeleton } from "@/components/ui/skeleton";

type RunDetailViewProps = {
  readonly summary: EvaluationRunSummary | null;
  readonly detail: EvaluationRunDetail | null;
  readonly loading?: boolean;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

function stringField(record: Record<string, unknown> | null, key: string): string | null {
  const value = record?.[key];
  return typeof value === "string" ? value : null;
}

function numberField(record: Record<string, unknown> | null, key: string): number | null {
  const value = record?.[key];
  return typeof value === "number" ? value : null;
}

export function RunDetailView({
  summary,
  detail,
  loading = false,
}: RunDetailViewProps): React.JSX.Element {
  if (loading) {
    return (
      <div className="space-y-3" aria-busy="true" aria-label="Loading run details">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!summary) {
    return (
      <p className="text-sm text-muted-foreground">
        Select a run from the recent list to inspect details.
      </p>
    );
  }

  const config = asRecord(detail?.config ?? null);
  const summaryPayload = asRecord(detail?.summary ?? null);
  const failing =
    summary.failing_metrics.length > 0
      ? summary.failing_metrics
      : Array.isArray(summaryPayload?.failing_metrics)
        ? (summaryPayload.failing_metrics as string[])
        : [];

  return (
    <article className="space-y-4 rounded-lg border border-border bg-card p-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold tracking-tight">{summary.name}</h2>
          <p className="font-mono text-xs text-muted-foreground">
            {shortRunId(summary.run_id)} · {summary.dataset_id}@{summary.dataset_version}
          </p>
        </div>
        <StatusChip status={summary.status} />
      </header>

      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
        <span className="rounded border border-border px-2 py-1">top_k={summary.top_k}</span>
        <span className="rounded border border-border px-2 py-1">
          prompt {summary.prompt_version}
        </span>
        <span className="rounded border border-border px-2 py-1">{summary.llm}</span>
        {config ? (
          <span className="rounded border border-border px-2 py-1">
            embedding {stringField(config, "embedding_model") ?? "—"}
          </span>
        ) : null}
      </div>

      <section className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Experiment summary
        </h3>
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">Questions</dt>
            <dd className="font-mono tabular-nums">{summary.question_count}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Errors</dt>
            <dd className="font-mono tabular-nums">{summary.error_count}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">MRR</dt>
            <dd className="font-mono tabular-nums">{formatMetric(summary.mrr)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Abstention precision</dt>
            <dd className="font-mono tabular-nums">{formatMetric(summary.abstention_precision)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">e2e p50</dt>
            <dd className="font-mono tabular-nums">{formatLatencyMs(summary.e2e_p50_ms)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Citation precision</dt>
            <dd className="font-mono tabular-nums">
              {formatMetric(summary.citation_precision_mean)}
            </dd>
          </div>
        </dl>
      </section>

      <section className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Failing gates
        </h3>
        {failing.length === 0 ? (
          <p className="text-sm text-muted-foreground">—</p>
        ) : (
          <ul className="flex flex-wrap gap-1">
            {failing.map((metric) => (
              <li
                key={metric}
                className="rounded bg-destructive/10 px-2 py-0.5 text-xs text-destructive"
              >
                {metric}
              </li>
            ))}
          </ul>
        )}
      </section>

      <MetricStatGrid run={summary} />

      <div className="flex flex-wrap gap-2">
        <Button asChild variant="outline" size="sm">
          <Link to={`/experiments/${summary.run_id}`}>View full results</Link>
        </Button>
        <Button asChild variant="ghost" size="sm">
          <Link to="/experiments/compare">Compare…</Link>
        </Button>
      </div>

      {config ? (
        <p className="text-xs text-muted-foreground">
          min_evidence_score=
          {formatMetric(numberField(config, "min_evidence_score"), {
            decimals: 2,
          })}
        </p>
      ) : null}
    </article>
  );
}
