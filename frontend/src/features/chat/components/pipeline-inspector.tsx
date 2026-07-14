import { useMutation } from "@tanstack/react-query";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { retrieveChunks } from "@/features/chat/api";
import { CollapsiblePanel } from "@/features/chat/components/collapsible-panel";
import { SimilarityBar } from "@/features/chat/components/similarity-bar";
import type { ChatMessage, RetrieveResponse } from "@/features/chat/types";
import { isApiError } from "@/lib/api/types";

type PipelineInspectorProps = {
  readonly message: ChatMessage | null;
  readonly knowledgeBaseId: string | null;
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
};

/**
 * Operator diagnostics for the last turn.
 * Streaming-ready: fields mirror future SSE pipeline events without consuming streams.
 */
export function PipelineInspector({
  message,
  knowledgeBaseId,
  open,
  onOpenChange,
}: PipelineInspectorProps): React.JSX.Element {
  const [debugBundle, setDebugBundle] = React.useState<{
    readonly messageId: string;
    readonly result: RetrieveResponse;
  } | null>(null);

  const debugResult = message && debugBundle?.messageId === message.id ? debugBundle.result : null;

  const mutation = useMutation({
    mutationFn: () => {
      if (!message?.sourceQuestion || !knowledgeBaseId) {
        throw new Error("Missing question or knowledge base");
      }
      return retrieveChunks({
        query: message.sourceQuestion,
        knowledge_base_id: knowledgeBaseId,
        top_k: message.topK ?? 8,
      });
    },
    onSuccess: (data) => {
      if (!message) return;
      setDebugBundle({ messageId: message.id, result: data });
    },
  });

  return (
    <CollapsiblePanel
      title="Pipeline inspector"
      open={open}
      onOpenChange={onOpenChange}
      defaultOpen={false}
      headerExtra={
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={!message?.sourceQuestion || !knowledgeBaseId || mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          Re-run retrieval
        </Button>
      }
    >
      {!message ? (
        <p className="text-sm text-muted-foreground">
          Pipeline steps appear after a turn completes.
        </p>
      ) : (
        <div className="space-y-3 text-sm">
          <ol className="space-y-2">
            <li className="rounded-md border border-border p-2">
              <p className="text-xs font-semibold uppercase text-muted-foreground">1. Question</p>
              <p className="mt-1">{message.sourceQuestion ?? "—"}</p>
            </li>
            <li className="rounded-md border border-border p-2">
              <p className="text-xs font-semibold uppercase text-muted-foreground">2. Retrieval</p>
              <p className="mt-1 text-muted-foreground">
                top_k={message.topK ?? "—"} · chunks=
                {message.retrievedChunks?.length ?? 0}
              </p>
              {(debugResult?.results ?? message.retrievedChunks)?.length ? (
                <ul className="mt-2 space-y-1">
                  {(debugResult?.results ?? message.retrievedChunks ?? [])
                    .slice(0, 5)
                    .map((chunk, index) => (
                      <li
                        key={chunk.chunk_id}
                        className="flex items-center justify-between gap-2 text-xs"
                      >
                        <span className="truncate">
                          #{index + 1} {chunk.heading ?? chunk.chunk_id.slice(0, 8)}
                        </span>
                        <SimilarityBar score={chunk.score} className="w-28" />
                      </li>
                    ))}
                </ul>
              ) : null}
              {mutation.isPending ? <Skeleton className="mt-2 h-8 w-full" /> : null}
              {mutation.isError ? (
                <p className="mt-2 text-xs text-destructive" role="alert">
                  {isApiError(mutation.error) ? mutation.error.message : "Retrieve failed"}
                </p>
              ) : null}
              {debugResult ? (
                <p className="mt-2 text-xs text-muted-foreground">
                  Debug re-run returned {debugResult.result_count} chunks
                </p>
              ) : null}
            </li>
            <li className="rounded-md border border-border p-2">
              <p className="text-xs font-semibold uppercase text-muted-foreground">3. Generation</p>
              <p className="mt-1 text-muted-foreground">
                status={message.status ?? "—"} · streaming=
                {message.streamingState}
                {message.modelKey ? ` · model=${message.modelKey}` : ""}
                {message.promptTemplateVersion ? ` · prompt=${message.promptTemplateVersion}` : ""}
              </p>
            </li>
            <li className="rounded-md border border-border p-2">
              <p className="text-xs font-semibold uppercase text-muted-foreground">4. Citations</p>
              <p className="mt-1 text-muted-foreground">
                {message.citations?.length ?? 0} citation(s)
                {message.warnings && message.warnings.length > 0
                  ? ` · warnings: ${message.warnings.join(", ")}`
                  : ""}
              </p>
            </li>
          </ol>
          <p className="text-xs text-muted-foreground">
            Streaming transport is reserved for a future release; this panel already surfaces
            per-stage fields.
          </p>
        </div>
      )}
    </CollapsiblePanel>
  );
}
