export const chatKeys = {
  all: ["chat"] as const,
  conversations: () => [...chatKeys.all, "conversations"] as const,
  conversation: (id: string) => [...chatKeys.conversations(), id] as const,
  retrieveDebug: (conversationId: string, messageId: string) =>
    [...chatKeys.all, "retrieve-debug", conversationId, messageId] as const,
};
