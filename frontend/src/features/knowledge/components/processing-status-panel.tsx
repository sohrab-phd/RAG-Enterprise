import * as React from "react";

import { StatusChip } from "@/features/knowledge/components/status-chip";
import { PROCESSING_STEPS, stepState } from "@/features/knowledge/lib/format";
import type { DocumentVersionSummary } from "@/features/knowledge/types";
import { cn } from "@/lib/utils";

type ProcessingStatusPanelProps = {
  readonly version: DocumentVersionSummary | null;
  readonly hasCurrentVersion: boolean;
};

export function ProcessingStatusPanel({
  version,
  hasCurrentVersion,
}: ProcessingStatusPanelProps): React.JSX.Element {
  if (!version && !hasCurrentVersion) {
    return (
      <p className="text-sm text-muted-foreground">
        Upload a file to create the first version and start processing.
      </p>
    );
  }

  if (!version) {
    return (
      <p className="text-sm text-muted-foreground">
        A current version exists. Detailed processing status is available after upload (version
        status API not exposed for polling yet).
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-medium">
          Version v{version.version_number} · {version.file_name}
        </p>
        <StatusChip status={version.processing_status} />
      </div>
      <ol className="space-y-2">
        {PROCESSING_STEPS.map((step) => {
          const state = stepState(version.processing_status, step.key);
          return (
            <li key={step.key} className="flex items-center justify-between gap-2 text-sm">
              <span>{step.label}</span>
              <span
                className={cn(
                  "text-xs font-medium uppercase tracking-wide",
                  state === "done" && "text-success",
                  state === "in_progress" && "text-info",
                  state === "pending" && "text-muted-foreground",
                  state === "failed" && "text-destructive",
                )}
              >
                {state === "in_progress" ? "in progress" : state}
              </span>
            </li>
          );
        })}
      </ol>
      <p className="text-xs text-muted-foreground" aria-live="polite">
        processing_status: {version.processing_status}
      </p>
    </div>
  );
}
