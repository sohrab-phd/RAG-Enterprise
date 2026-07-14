import { MessageSquarePlus, Trash2 } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import type { ConversationSummary } from "@/features/chat/types";
import { EmptyState } from "@/features/knowledge/components/empty-state";
import { formatRelativeTime } from "@/features/knowledge/lib/format";
import { cn } from "@/lib/utils";

type ConversationListProps = {
  readonly conversations: readonly ConversationSummary[];
  readonly activeId: string | null;
  readonly onSelect: (id: string) => void;
  readonly onNew: () => void;
  readonly onDelete: (id: string) => void;
};

export function ConversationList({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
}: ConversationListProps): React.JSX.Element {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between gap-2 border-b border-border p-3">
        <h2 className="text-sm font-semibold">Conversations</h2>
        <Button type="button" size="sm" variant="outline" onClick={onNew}>
          <MessageSquarePlus className="size-4" aria-hidden />
          New
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-2">
        {conversations.length === 0 ? (
          <EmptyState
            title="No conversations yet"
            description="Ask a question to start."
            className="border-0 bg-transparent p-3"
          />
        ) : (
          <ul className="space-y-1">
            {conversations.map((item) => {
              const active = item.id === activeId;
              return (
                <li key={item.id} className="group relative">
                  <button
                    type="button"
                    className={cn(
                      "w-full rounded-md px-2 py-2 pr-9 text-left text-sm hover:bg-muted/60",
                      active && "bg-muted",
                    )}
                    onClick={() => onSelect(item.id)}
                    aria-current={active ? "true" : undefined}
                  >
                    <span className="line-clamp-2 font-medium">{item.title}</span>
                    <span className="mt-0.5 block text-xs text-muted-foreground">
                      {formatRelativeTime(item.updatedAt)}
                    </span>
                  </button>
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="absolute right-1 top-1 opacity-0 group-hover:opacity-100 focus:opacity-100"
                    aria-label={`Delete conversation ${item.title}`}
                    onClick={() => onDelete(item.id)}
                  >
                    <Trash2 className="size-3.5" aria-hidden />
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
