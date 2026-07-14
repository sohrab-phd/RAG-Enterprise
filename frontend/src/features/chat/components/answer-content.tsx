import * as React from "react";

import type { Citation } from "@/features/chat/types";
import { cn } from "@/lib/utils";

type AnswerContentProps = {
  readonly answer: string;
  readonly citations: readonly Citation[];
  readonly activeMarker: string | null;
  readonly onSelectMarker: (marker: string) => void;
};

const MARKER_PATTERN = /(\[\d+\])/g;

export function AnswerContent({
  answer,
  citations,
  activeMarker,
  onSelectMarker,
}: AnswerContentProps): React.JSX.Element {
  const known = new Set(citations.map((item) => item.marker));
  const parts = answer.split(MARKER_PATTERN);

  return (
    <p className="whitespace-pre-wrap text-sm leading-relaxed">
      {parts.map((part, index) => {
        if (known.has(part)) {
          const active = activeMarker === part;
          return (
            <button
              key={`marker-${part}-${index}`}
              type="button"
              className={cn(
                "mx-0.5 inline rounded px-1 font-mono text-xs font-semibold",
                "bg-primary/10 text-primary hover:bg-primary/20",
                active && "ring-2 ring-ring",
              )}
              onClick={(event) => {
                event.stopPropagation();
                onSelectMarker(part);
              }}
              aria-label={`Citation ${part}`}
            >
              {part}
            </button>
          );
        }
        return <React.Fragment key={`text-${index}`}>{part}</React.Fragment>;
      })}
    </p>
  );
}
