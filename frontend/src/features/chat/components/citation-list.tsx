import * as React from "react";
import { Link } from "react-router-dom";

import { SimilarityBar } from "@/features/chat/components/similarity-bar";
import type { Citation } from "@/features/chat/types";
import { cn } from "@/lib/utils";

type CitationListProps = {
  readonly citations: readonly Citation[];
  readonly activeMarker: string | null;
  readonly onSelectMarker: (marker: string) => void;
  readonly knowledgeBaseId: string;
};

export function CitationList({
  citations,
  activeMarker,
  onSelectMarker,
  knowledgeBaseId,
}: CitationListProps): React.JSX.Element {
  if (citations.length === 0) {
    return <p className="text-sm text-muted-foreground">No citations for this turn.</p>;
  }

  return (
    <ul className="space-y-2">
      {citations.map((citation) => {
        const active = activeMarker === citation.marker;
        return (
          <li key={`${citation.chunk_id}-${citation.marker}`}>
            <button
              type="button"
              className={cn(
                "w-full rounded-md border border-border p-2 text-left text-sm transition-colors hover:bg-muted/50",
                active && "border-primary bg-primary/5",
              )}
              onClick={() => onSelectMarker(citation.marker)}
            >
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="font-mono text-xs font-semibold">{citation.marker}</span>
                <SimilarityBar score={citation.relevance_score} />
              </div>
              <p className="line-clamp-3 text-muted-foreground">{citation.excerpt}</p>
              <Link
                to={`/knowledge/${knowledgeBaseId}?documentId=${citation.document_id}`}
                className="mt-1 inline-block text-xs font-medium text-foreground underline-offset-2 hover:underline"
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
