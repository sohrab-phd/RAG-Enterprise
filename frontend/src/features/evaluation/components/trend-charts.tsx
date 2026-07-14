import * as React from "react";
import { Link } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  formatLatencyMs,
  formatMetric,
  runsChronological,
  shortRunId,
} from "@/features/evaluation/lib/format";
import type { EvaluationRunSummary } from "@/features/evaluation/types";

type TrendChartsProps = {
  readonly runs: readonly EvaluationRunSummary[];
};

type ChartPoint = {
  readonly label: string;
  readonly groundedness: number | null;
  readonly recall_at_k: number | null;
  readonly citation_accuracy: number | null;
  readonly retrieval_latency_mean_ms: number | null;
};

function toPoints(runs: readonly EvaluationRunSummary[]): ChartPoint[] {
  return runsChronological(runs).map((run) => ({
    label: shortRunId(run.run_id),
    groundedness: run.groundedness,
    recall_at_k: run.recall_at_k,
    citation_accuracy: run.citation_accuracy,
    retrieval_latency_mean_ms: run.retrieval_latency_mean_ms,
  }));
}

type SingleChartProps = {
  readonly title: string;
  readonly data: readonly ChartPoint[];
  readonly dataKey: keyof Omit<ChartPoint, "label">;
  readonly formatTick?: (value: number) => string;
  readonly formatTooltip?: (value: number) => string;
};

function SingleTrendChart({
  title,
  data,
  dataKey,
  formatTick = (value) => formatMetric(value),
  formatTooltip = formatTick,
}: SingleChartProps): React.JSX.Element {
  const hasData = data.some((point) => point[dataKey] != null);

  return (
    <section className="rounded-lg border border-border bg-card p-3">
      <header className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        {!hasData ? <span className="text-xs text-muted-foreground">No data</span> : null}
      </header>
      <div className="h-44 w-full">
        {hasData ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={[...data]} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} className="text-muted-foreground" />
              <YAxis
                tick={{ fontSize: 11 }}
                width={48}
                tickFormatter={(value: number) => formatTick(value)}
                className="text-muted-foreground"
              />
              <Tooltip
                formatter={(value) => (typeof value === "number" ? formatTooltip(value) : "—")}
                labelFormatter={(label) => `Run ${String(label)}`}
              />
              <Line
                type="monotone"
                dataKey={dataKey}
                stroke="var(--color-primary)"
                strokeWidth={2}
                dot={{ r: 3 }}
                connectNulls
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Not enough completed runs to chart.
          </div>
        )}
      </div>
    </section>
  );
}

export function TrendCharts({ runs }: TrendChartsProps): React.JSX.Element {
  const points = toPoints(runs);

  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Trend charts</h2>
          <p className="text-xs text-muted-foreground">
            Lightweight history across filtered runs (measurement only).
          </p>
        </div>
        <Link
          to="/experiments"
          className="text-xs font-medium text-foreground underline-offset-2 hover:underline"
        >
          Open experiments
        </Link>
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        <SingleTrendChart title="Groundedness" data={points} dataKey="groundedness" />
        <SingleTrendChart title="Recall@K" data={points} dataKey="recall_at_k" />
        <SingleTrendChart title="Citation accuracy" data={points} dataKey="citation_accuracy" />
        <SingleTrendChart
          title="Retrieval latency"
          data={points}
          dataKey="retrieval_latency_mean_ms"
          formatTick={(value) => `${Math.round(value)}`}
          formatTooltip={(value) => formatLatencyMs(value)}
        />
      </div>
    </div>
  );
}
