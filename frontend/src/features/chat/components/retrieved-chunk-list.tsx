import * as React from "react";
import { Link } from "react-router-dom";

import { SimilarityBar } from "@/features/chat/components/similarity-bar";
import type { Citation, RetrievedChunk } from "@/features/chat/types";
import { cn } from "@/lib/utils";

type RetrievedChunkListProps = {
  readonly chunks: readonly RetrievedChunk[];
  readonly citations: readonly Citation[];
  readonly activeChunkId: string | null;
  readonly onSelectChunk: (chunkId: string) => void;
  readonly knowledgeBaseId: string;
};

export function RetrievedChunkList({
  chunks,
  citations,
  activeChunkId,
  onSelectChunk,
  knowledgeBaseId,
}: RetrievedChunkListProps): React.JSX.Element {
  const citedIds = new Set(citations.map((item) => item.chunk_id));
  const [expandedId, setExpandedId] = React.useState<string | null>(null);

  if (chunks.length === 0) {
    return <p className="text-sm text-muted-foreground">No chunks retrieved.</p>;
  }

  return (
    <ul className="space-y-2">
      {chunks.map((chunk, index) => {
        const active = activeChunkId === chunk.chunk_id;
        const cited = citedIds.has(chunk.chunk_id);
        const expanded = expandedId === chunk.chunk_id;
        return (
          <li key={chunk.chunk_id}>
            <button
              type="button"
              className={cn(
                "w-full rounded-md border border-border p-2 text-left text-sm transition-colors hover:bg-muted/50",
                active && "border-primary bg-primary/5",
                cited && "ring-1 ring-success/40",
              )}
              onClick={() => {
                onSelectChunk(chunk.chunk_id);
                setExpandedId((current) => (current === chunk.chunk_id ? null : chunk.chunk_id));
              }}
            >
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-muted-foreground">
                  #{index + 1}
                  {cited ? " · cited" : ""}
                  {chunk.heading ? ` · ${chunk.heading}` : ""}
                </span>
                <SimilarityBar score={chunk.score} />
              </div>
              <p className={cn(!expanded && "line-clamp-3", "text-foreground")}>{chunk.text}</p>
              <Link
                to={`/knowledge/${knowledgeBaseId}?documentId=${chunk.document_id}`}
                className="mt-1 inline-block text-xs font-medium underline-offset-2 hover:underline"
                onClick={(event) => event.stopPropagation()}
              >
                Open document
              </Link>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
