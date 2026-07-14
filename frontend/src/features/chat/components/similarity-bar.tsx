import * as React from "react";

import { cn } from "@/lib/utils";

type SimilarityBarProps = {
  readonly score: number;
  readonly className?: string;
};

export function SimilarityBar({ score, className }: SimilarityBarProps): React.JSX.Element {
  const clamped = Math.max(0, Math.min(1, score));
  const percent = Math.round(clamped * 100);

  return (
    <div className={cn("flex min-w-[5rem] items-center gap-2", className)}>
      <div
        className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted"
        role="meter"
        aria-label={`Similarity ${clamped.toFixed(2)}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
      >
        <div className="h-full rounded-full bg-primary" style={{ width: `${percent}%` }} />
      </div>
      <span className="w-10 shrink-0 text-right font-mono text-xs tabular-nums text-muted-foreground">
        {clamped.toFixed(2)}
      </span>
    </div>
  );
}
