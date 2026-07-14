import * as React from "react";

import { Button } from "@/components/ui/button";
import { AnswerContent } from "@/features/chat/components/answer-content";
import type { ChatMessage } from "@/features/chat/types";
import { StatusChip } from "@/features/knowledge/components/status-chip";
import { EmptyState } from "@/features/knowledge/components/empty-state";
import { cn } from "@/lib/utils";

type MessageThreadProps = {
  readonly messages: readonly ChatMessage[];
  readonly activeMarker: string | null;
  readonly onSelectMarker: (marker: string) => void;
  readonly onSelectAssistant: (messageId: string) => void;
  readonly selectedAssistantId: string | null;
  readonly onRetry?: (message: ChatMessage) => void;
};

export function MessageThread({
  messages,
  activeMarker,
  onSelectMarker,
  onSelectAssistant,
  selectedAssistantId,
  onRetry,
}: MessageThreadProps): React.JSX.Element {
  const bottomRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <EmptyState
          title="Ask a question grounded in this knowledge base"
          description="Answers include citations and retrieved evidence. Select a knowledge base before sending."
          className="max-w-md"
        />
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-auto p-4" aria-live="polite">
      {messages.map((message) => {
        const isUser = message.role === "user";
        const selected = !isUser && selectedAssistantId === message.id;
        const pending =
          message.streamingState === "pending" || message.streamingState === "streaming";

        return (
          <article
            key={message.id}
            className={cn(
              "max-w-[92%] rounded-lg border border-border px-3 py-2 shadow-sm",
              isUser
                ? "ml-auto bg-secondary text-secondary-foreground"
                : "mr-auto cursor-pointer bg-card",
              selected && "ring-2 ring-ring",
            )}
            onClick={
              isUser
                ? undefined
                : () => {
                    onSelectAssistant(message.id);
                  }
            }
          >
            <header className="mb-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span className="font-medium text-foreground">{isUser ? "User" : "Assistant"}</span>
              {!isUser && message.status ? <StatusChip status={message.status} /> : null}
              {!isUser && message.clientLatencyMs != null ? (
                <span>{message.clientLatencyMs} ms</span>
              ) : null}
              {pending ? <span>Retrieving and generating…</span> : null}
            </header>

            {isUser ? (
              <p className="whitespace-pre-wrap text-sm">{message.content}</p>
            ) : pending && !message.content ? (
              <p className="text-sm text-muted-foreground">Retrieving and generating…</p>
            ) : message.status === "failed" ? (
              <div className="space-y-2">
                <p className="text-sm text-destructive" role="alert">
                  {message.failureReason ?? message.content ?? "Turn failed"}
                </p>
                {onRetry && message.sourceQuestion ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={(event) => {
                      event.stopPropagation();
                      onRetry(message);
                    }}
                  >
                    Retry
                  </Button>
                ) : null}
              </div>
            ) : message.abstained ? (
              <div
                role="status"
                className="rounded-md border border-warning/40 bg-warning/10 px-2 py-1.5 text-sm"
              >
                <p className="font-medium">Abstained</p>
                <p className="text-muted-foreground">
                  {message.abstentionReason ?? message.content}
                </p>
              </div>
            ) : (
              <AnswerContent
                answer={message.content}
                citations={message.citations ?? []}
                activeMarker={activeMarker}
                onSelectMarker={(marker) => {
                  onSelectAssistant(message.id);
                  onSelectMarker(marker);
                }}
              />
            )}

            {!isUser && message.warnings && message.warnings.length > 0 ? (
              <ul className="mt-2 flex flex-wrap gap-1">
                {message.warnings.map((warning) => (
                  <li
                    key={warning}
                    className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                  >
                    {warning}
                  </li>
                ))}
              </ul>
            ) : null}
          </article>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
