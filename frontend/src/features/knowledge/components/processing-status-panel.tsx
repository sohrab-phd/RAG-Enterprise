import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/types";
import { processAndIndexDocument } from "@/features/knowledge/api";
import { StatusChip } from "@/features/knowledge/components/status-chip";
import { PROCESSING_STEPS, stepState } from "@/features/knowledge/lib/format";
import { knowledgeKeys } from "@/features/knowledge/query-keys";
import type { DocumentVersionSummary } from "@/features/knowledge/types";
import { cn } from "@/lib/utils";

type ProcessingStatusPanelProps = {
  readonly knowledgeBaseId: string;
  readonly documentId: string;
  readonly version: DocumentVersionSummary | null;
  readonly hasCurrentVersion: boolean;
};

const OPTIMISTIC_STAGES = ["extracting", "chunking", "indexing"] as const;

export function ProcessingStatusPanel({
  knowledgeBaseId,
  documentId,
  version,
  hasCurrentVersion,
}: ProcessingStatusPanelProps): React.JSX.Element {
  const queryClient = useQueryClient();
  const [optimisticStatus, setOptimisticStatus] = React.useState<string | null>(null);
  const [actionError, setActionError] = React.useState<string | null>(null);

  const processMutation = useMutation({
    mutationFn: () => processAndIndexDocument(documentId),
    onMutate: () => {
      setActionError(null);
      setOptimisticStatus("extracting");
    },
    onSuccess: (result) => {
      setOptimisticStatus(null);
      if (version) {
        queryClient.setQueryData<DocumentVersionSummary>(
          knowledgeKeys.lastVersion(knowledgeBaseId, documentId),
          {
            ...version,
            id: result.document_version_id ?? version.id,
            processing_status: result.current_status,
          },
        );
      } else if (result.document_version_id) {
        queryClient.setQueryData<DocumentVersionSummary>(
          knowledgeKeys.lastVersion(knowledgeBaseId, documentId),
          {
            id: result.document_version_id,
            version_number: 1,
            extraction_method: "native_text",
            processing_status: result.current_status,
            content_hash: "",
            file_name: "processed",
            file_size_bytes: 0,
            mime_type: "application/octet-stream",
            is_current: true,
            created_at: new Date().toISOString(),
          },
        );
      }
      void queryClient.invalidateQueries({
        queryKey: knowledgeKeys.document(knowledgeBaseId, documentId),
      });
    },
    onError: (error: unknown) => {
      setOptimisticStatus(null);
      const detailsStatus =
        error instanceof ApiError &&
        error.details &&
        typeof error.details === "object" &&
        !Array.isArray(error.details) &&
        typeof error.details.current_status === "string"
          ? error.details.current_status
          : null;
      if (detailsStatus && version) {
        queryClient.setQueryData<DocumentVersionSummary>(
          knowledgeKeys.lastVersion(knowledgeBaseId, documentId),
          { ...version, processing_status: detailsStatus },
        );
      }
      setActionError(error instanceof Error ? error.message : "Process & Index failed");
    },
  });

  React.useEffect(() => {
    if (!processMutation.isPending) {
      return;
    }
    let index = 0;
    const timer = window.setInterval(() => {
      index = Math.min(index + 1, OPTIMISTIC_STAGES.length - 1);
      setOptimisticStatus(OPTIMISTIC_STAGES[index] ?? "indexing");
    }, 700);
    return () => window.clearInterval(timer);
  }, [processMutation.isPending]);

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
        A current version exists. Upload again in this session, or run Process & Index after upload
        to refresh status.
      </p>
    );
  }

  const displayStatus = optimisticStatus ?? version.processing_status;
  const canProcess =
    version.processing_status === "uploaded" ||
    version.processing_status === "failed" ||
    version.processing_status === "extracted" ||
    version.processing_status === "chunked";

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-medium">
          Version v{version.version_number} · {version.file_name}
        </p>
        <StatusChip status={displayStatus} />
      </div>
      <ol className="space-y-2">
        {PROCESSING_STEPS.map((step) => {
          const state = stepState(displayStatus, step.key);
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
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          onClick={() => processMutation.mutate()}
          disabled={processMutation.isPending || !canProcess}
          aria-busy={processMutation.isPending}
        >
          {processMutation.isPending
            ? "Processing…"
            : version.processing_status === "indexed"
              ? "Indexed"
              : "Process & Index"}
        </Button>
        {version.processing_status === "indexed" ? (
          <span className="text-xs text-muted-foreground">Ready for retrieval and chat</span>
        ) : null}
      </div>
      <p className="text-xs text-muted-foreground" aria-live="polite">
        processing_status: {displayStatus}
      </p>
      {actionError ? (
        <p className="text-sm text-destructive" role="alert">
          {actionError}
        </p>
      ) : null}
    </div>
  );
}
