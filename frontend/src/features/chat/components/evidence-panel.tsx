import * as React from "react";

import { StatusChip } from "@/features/knowledge/components/status-chip";
import { CitationList } from "@/features/chat/components/citation-list";
import { CollapsiblePanel } from "@/features/chat/components/collapsible-panel";
import { RetrievedChunkList } from "@/features/chat/components/retrieved-chunk-list";
import type { ChatMessage } from "@/features/chat/types";
import { EmptyState } from "@/features/knowledge/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";

type EvidencePanelProps = {
  readonly message: ChatMessage | null;
  readonly knowledgeBaseId: string | null;
  readonly loading?: boolean;
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly activeMarker: string | null;
  readonly onSelectMarker: (marker: string) => void;
};

export function EvidencePanel({
  message,
  knowledgeBaseId,
  loading = false,
  open,
  onOpenChange,
  activeMarker,
  onSelectMarker,
}: EvidencePanelProps): React.JSX.Element {
  const [manualChunkId, setManualChunkId] = React.useState<string | null>(null);

  const markerChunkId =
    activeMarker && message?.citations
      ? (message.citations.find((item) => item.marker === activeMarker)?.chunk_id ?? null)
      : null;
  const activeChunkId = markerChunkId ?? manualChunkId;

  return (
    <CollapsiblePanel
      title="Evidence"
      open={open}
      onOpenChange={onOpenChange}
      className="border-b-0"
    >
      {loading ? (
        <div className="space-y-2" aria-busy="true" aria-label="Loading evidence">
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : null}

      {!loading && !message ? (
        <EmptyState
          title="Evidence appears after each answer"
          description="Citations, retrieved chunks, and similarity scores show here."
          className="border-0 bg-transparent p-0"
        />
      ) : null}

      {!loading && message ? (
        <div className="space-y-4" key={message.id}>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <StatusChip status={message.status ?? "unknown"} />
            <span>{message.modelKey ?? "—"}</span>
            <span>·</span>
            <span>prompt {message.promptTemplateVersion ?? "—"}</span>
            <span>·</span>
            <span>
              e2e {message.clientLatencyMs != null ? `${message.clientLatencyMs} ms` : "—"}
            </span>
          </div>

          {message.abstained ? (
            <div
              role="status"
              className="rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-sm"
            >
              Abstained
              {message.abstentionReason ? `: ${message.abstentionReason}` : ""}
            </div>
          ) : null}

          {message.status === "failed" ? (
            <div
              role="alert"
              className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm"
            >
              {message.failureReason ?? "Generation failed"}
            </div>
          ) : null}

          {knowledgeBaseId ? (
            <>
              <div>
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Citations
                </h4>
                <CitationList
                  citations={message.citations ?? []}
                  activeMarker={activeMarker}
                  onSelectMarker={onSelectMarker}
                  knowledgeBaseId={knowledgeBaseId}
                />
              </div>
              <div>
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Retrieved chunks
                </h4>
                <RetrievedChunkList
                  chunks={message.retrievedChunks ?? []}
                  citations={message.citations ?? []}
                  activeChunkId={activeChunkId}
                  onSelectChunk={setManualChunkId}
                  knowledgeBaseId={knowledgeBaseId}
                />
              </div>
            </>
          ) : null}
        </div>
      ) : null}
    </CollapsiblePanel>
  );
}
