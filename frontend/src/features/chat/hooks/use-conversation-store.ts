import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";

import {
  deleteConversation,
  getConversation,
  loadConversations,
  toSummaries,
  upsertConversation,
} from "@/features/chat/conversation-store";
import { chatKeys } from "@/features/chat/query-keys";
import type { ConversationRecord, ConversationSummary } from "@/features/chat/types";

export function useConversationList(): {
  readonly conversations: readonly ConversationSummary[];
  readonly refresh: () => void;
} {
  const query = useQuery({
    queryKey: chatKeys.conversations(),
    queryFn: async () => toSummaries(loadConversations()),
    staleTime: Infinity,
  });

  const queryClient = useQueryClient();
  const refresh = React.useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
  }, [queryClient]);

  return {
    conversations: query.data ?? [],
    refresh,
  };
}

export function useConversationRecord(conversationId: string | null): {
  readonly record: ConversationRecord | null;
  readonly isReady: boolean;
  readonly save: (record: ConversationRecord) => void;
  readonly remove: (id: string) => void;
} {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: chatKeys.conversation(conversationId ?? "new"),
    queryFn: async () => {
      if (!conversationId) return null;
      return getConversation(conversationId) ?? null;
    },
    enabled: Boolean(conversationId),
    staleTime: Infinity,
  });

  const save = React.useCallback(
    (record: ConversationRecord) => {
      upsertConversation(record);
      queryClient.setQueryData(chatKeys.conversation(record.id), record);
      void queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
    },
    [queryClient],
  );

  const remove = React.useCallback(
    (id: string) => {
      deleteConversation(id);
      queryClient.removeQueries({ queryKey: chatKeys.conversation(id) });
      void queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
    },
    [queryClient],
  );

  return {
    record: conversationId ? (query.data ?? null) : null,
    isReady: !conversationId || query.isFetched,
    save,
    remove,
  };
}
