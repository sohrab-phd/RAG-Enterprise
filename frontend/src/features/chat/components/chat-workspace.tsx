import { useMutation, useQuery } from "@tanstack/react-query";
import * as React from "react";
import { useNavigate, useParams } from "react-router-dom";

import { sendChatTurn } from "@/features/chat/api";
import { ConversationList } from "@/features/chat/components/conversation-list";
import { EvidencePanel } from "@/features/chat/components/evidence-panel";
import { MessageThread } from "@/features/chat/components/message-thread";
import { PipelineInspector } from "@/features/chat/components/pipeline-inspector";
import { PromptComposer } from "@/features/chat/components/prompt-composer";
import { titleFromQuestion } from "@/features/chat/conversation-store";
import {
  useConversationList,
  useConversationRecord,
} from "@/features/chat/hooks/use-conversation-store";
import type { ChatMessage, ConversationRecord } from "@/features/chat/types";
import { listKnowledgeBases } from "@/features/knowledge/api";
import { knowledgeKeys } from "@/features/knowledge/query-keys";
import { isApiError } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

function createId(): string {
  return crypto.randomUUID();
}

function buildAssistantFromResponse(args: {
  readonly response: Awaited<ReturnType<typeof sendChatTurn>>;
  readonly question: string;
  readonly topK: number;
  readonly latencyMs: number;
  readonly messageId: string;
}): ChatMessage {
  const { response, question, topK, latencyMs, messageId } = args;
  return {
    id: messageId,
    role: "assistant",
    content: response.answer ?? "",
    createdAt: new Date().toISOString(),
    streamingState: response.status === "failed" ? "error" : "complete",
    status: response.status,
    citations: response.citations,
    retrievedChunks: response.retrieved_chunks,
    abstained: response.abstained,
    abstentionReason: response.abstention_reason,
    failureReason: response.failure_reason,
    modelKey: response.model_key,
    promptTemplateVersion: response.prompt_template_version,
    warnings: response.warnings,
    clientLatencyMs: latencyMs,
    sourceQuestion: question,
    topK,
  };
}

type SessionPaneProps = {
  readonly conversationId: string | null;
  readonly initialRecord: ConversationRecord | null;
  readonly conversations: ReturnType<typeof useConversationList>["conversations"];
  readonly save: (record: ConversationRecord) => void;
  readonly remove: (id: string) => void;
  readonly refresh: () => void;
  readonly onNavigateConversation: (id: string) => void;
  readonly onConversationLanded: (id: string) => void;
  readonly onNew: () => void;
};

function ChatSessionPane({
  conversationId,
  initialRecord,
  conversations,
  save,
  remove,
  refresh,
  onNavigateConversation,
  onConversationLanded,
  onNew,
}: SessionPaneProps): React.JSX.Element {
  const [knowledgeBaseId, setKnowledgeBaseId] = React.useState<string | null>(
    initialRecord?.knowledgeBaseId ?? null,
  );
  const [topK, setTopK] = React.useState(8);
  const [messages, setMessages] = React.useState<ChatMessage[]>(() => [
    ...(initialRecord?.messages ?? []),
  ]);
  const [selectedAssistantId, setSelectedAssistantId] = React.useState<string | null>(() => {
    const lastAssistant = [...(initialRecord?.messages ?? [])]
      .reverse()
      .find((item) => item.role === "assistant");
    return lastAssistant?.id ?? null;
  });
  const [activeMarker, setActiveMarker] = React.useState<string | null>(null);
  const [evidenceOpen, setEvidenceOpen] = React.useState(true);
  const [pipelineOpen, setPipelineOpen] = React.useState(false);
  const [mobilePane, setMobilePane] = React.useState<"list" | "chat" | "evidence">("chat");
  const [composerError, setComposerError] = React.useState<string | null>(null);

  const kbQuery = useQuery({
    queryKey: knowledgeKeys.baseList({ page: 1, pageSize: 100 }),
    queryFn: ({ signal }) => listKnowledgeBases({ page: 1, pageSize: 100, signal }),
  });

  const selectedAssistant =
    messages.find((item) => item.id === selectedAssistantId) ??
    [...messages].reverse().find((item) => item.role === "assistant") ??
    null;

  const persist = React.useCallback(
    (
      conversationKey: string,
      nextMessages: readonly ChatMessage[],
      kbId: string,
      titleHint?: string,
    ) => {
      const existingTitle =
        initialRecord?.id === conversationKey
          ? initialRecord.title
          : conversations.find((item) => item.id === conversationKey)?.title;
      const next: ConversationRecord = {
        id: conversationKey,
        title:
          existingTitle ??
          titleHint ??
          titleFromQuestion(
            nextMessages.find((item) => item.role === "user")?.content ?? "Conversation",
          ),
        knowledgeBaseId: kbId,
        updatedAt: new Date().toISOString(),
        messages: nextMessages,
      };
      save(next);
      refresh();
    },
    [conversations, initialRecord, refresh, save],
  );

  const mutation = useMutation({
    mutationFn: async (input: {
      readonly question: string;
      readonly knowledgeBaseId: string;
      readonly conversationId: string | null;
      readonly topK: number;
      readonly userMessageId: string;
      readonly assistantMessageId: string;
      readonly replaceAssistantId?: string;
    }) => {
      const started = performance.now();
      const response = await sendChatTurn({
        question: input.question,
        knowledge_base_id: input.knowledgeBaseId,
        conversation_id: input.conversationId,
        top_k: input.topK,
      });
      return {
        response,
        latencyMs: Math.round(performance.now() - started),
        ...input,
      };
    },
    onMutate: (input) => {
      setComposerError(null);
      const userMessage: ChatMessage = {
        id: input.userMessageId,
        role: "user",
        content: input.question,
        createdAt: new Date().toISOString(),
        streamingState: "complete",
      };
      const pendingAssistant: ChatMessage = {
        id: input.assistantMessageId,
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString(),
        streamingState: "pending",
        sourceQuestion: input.question,
        topK: input.topK,
      };
      setMessages((current) => {
        if (input.replaceAssistantId) {
          return current.map((item) =>
            item.id === input.replaceAssistantId ? pendingAssistant : item,
          );
        }
        return [...current, userMessage, pendingAssistant];
      });
      setSelectedAssistantId(input.assistantMessageId);
      setMobilePane("chat");
    },
    onSuccess: (result) => {
      const assistant = buildAssistantFromResponse({
        response: result.response,
        question: result.question,
        topK: result.topK,
        latencyMs: result.latencyMs,
        messageId: result.assistantMessageId,
      });

      setMessages((current) => {
        const next = current.map((item) =>
          item.id === result.assistantMessageId ? assistant : item,
        );
        const conversationKey =
          result.response.conversation_id ?? result.conversationId ?? createId();
        queueMicrotask(() => {
          persist(
            conversationKey,
            next,
            result.knowledgeBaseId,
            titleFromQuestion(result.question),
          );
          if (conversationKey !== conversationId) {
            onConversationLanded(conversationKey);
          }
        });
        return next;
      });
      setSelectedAssistantId(result.assistantMessageId);
      setEvidenceOpen(true);
    },
    onError: (error, input) => {
      const message = isApiError(error) ? error.message : "Failed to send message";
      if (isApiError(error) && error.code === "validation_failed") {
        setComposerError(message);
      }
      setMessages((current) =>
        current.map((item) =>
          item.id === input.assistantMessageId
            ? {
                ...item,
                streamingState: "error",
                status: "failed",
                failureReason: message,
                content: message,
              }
            : item,
        ),
      );
    },
  });

  const sendQuestion = (
    question: string,
    options?: { readonly replaceAssistantId?: string },
  ): void => {
    if (!knowledgeBaseId) {
      setComposerError("Select a knowledge base");
      return;
    }
    mutation.mutate({
      question,
      knowledgeBaseId,
      conversationId,
      topK,
      userMessageId: createId(),
      assistantMessageId: options?.replaceAssistantId ?? createId(),
      replaceAssistantId: options?.replaceAssistantId,
    });
  };

  const handleRetry = (message: ChatMessage): void => {
    if (!message.sourceQuestion || !knowledgeBaseId) return;
    sendQuestion(message.sourceQuestion, {
      replaceAssistantId: message.id,
    });
  };

  const handleDelete = (id: string): void => {
    remove(id);
    refresh();
    if (id === conversationId) {
      onNew();
    }
  };

  return (
    <>
      <div className="flex gap-2 lg:hidden">
        {(
          [
            ["list", "History"],
            ["chat", "Chat"],
            ["evidence", "Evidence"],
          ] as const
        ).map(([key, label]) => (
          <Button
            key={key}
            type="button"
            size="sm"
            variant={mobilePane === key ? "default" : "outline"}
            onClick={() => setMobilePane(key)}
          >
            {label}
          </Button>
        ))}
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 overflow-hidden rounded-lg border border-border bg-card lg:grid-cols-[220px_minmax(0,1fr)_320px] xl:grid-cols-[240px_minmax(0,1fr)_360px]">
        <aside
          className={cn(
            "min-h-0 border-b border-border lg:border-b-0 lg:border-r",
            mobilePane === "list" ? "block" : "hidden lg:block",
          )}
          aria-label="Conversation history"
        >
          <ConversationList
            conversations={conversations}
            activeId={conversationId}
            onSelect={(id) => {
              onNavigateConversation(id);
              setMobilePane("chat");
            }}
            onNew={onNew}
            onDelete={handleDelete}
          />
        </aside>

        <div
          className={cn(
            "flex min-h-0 min-w-0 flex-col border-b border-border lg:border-b-0 lg:border-r",
            mobilePane === "chat" ? "flex" : "hidden lg:flex",
          )}
        >
          <div className="border-b border-border px-3 py-2 text-xs text-muted-foreground">
            Evidence required · streaming reserved · no agents/tools
          </div>
          <MessageThread
            messages={messages}
            activeMarker={activeMarker}
            onSelectMarker={(marker) => {
              setActiveMarker(marker);
              setEvidenceOpen(true);
              setMobilePane("evidence");
            }}
            onSelectAssistant={(id) => {
              setSelectedAssistantId(id);
              setEvidenceOpen(true);
            }}
            selectedAssistantId={selectedAssistant?.id ?? null}
            onRetry={handleRetry}
          />
          {composerError ? (
            <p className="px-3 text-xs text-destructive" role="alert">
              {composerError}
            </p>
          ) : null}
          <PromptComposer
            knowledgeBases={kbQuery.data?.items ?? []}
            knowledgeBasesLoading={kbQuery.isLoading}
            knowledgeBaseId={knowledgeBaseId}
            onKnowledgeBaseChange={setKnowledgeBaseId}
            topK={topK}
            onTopKChange={setTopK}
            submitting={mutation.isPending}
            onSubmit={(question) => sendQuestion(question)}
          />
        </div>

        <aside
          className={cn(
            "flex min-h-0 flex-col overflow-auto",
            mobilePane === "evidence" ? "flex" : "hidden lg:flex",
          )}
          aria-label="Evidence and pipeline"
        >
          <EvidencePanel
            message={selectedAssistant}
            knowledgeBaseId={knowledgeBaseId}
            loading={
              selectedAssistant?.streamingState === "pending" ||
              selectedAssistant?.streamingState === "streaming"
            }
            open={evidenceOpen}
            onOpenChange={setEvidenceOpen}
            activeMarker={activeMarker}
            onSelectMarker={setActiveMarker}
          />
          <PipelineInspector
            message={selectedAssistant}
            knowledgeBaseId={knowledgeBaseId}
            open={pipelineOpen}
            onOpenChange={setPipelineOpen}
          />
        </aside>
      </div>
    </>
  );
}

export function ChatWorkspace(): React.JSX.Element {
  const { conversationId: routeConversationId } = useParams();
  const navigate = useNavigate();
  const { conversations, refresh } = useConversationList();
  const activeId = routeConversationId ?? null;
  const { record, save, remove, isReady } = useConversationRecord(activeId);
  const [paneKey, setPaneKey] = React.useState(0);

  const handleNew = (): void => {
    setPaneKey((value) => value + 1);
    navigate("/chat");
  };

  const handleSelectConversation = (id: string): void => {
    setPaneKey((value) => value + 1);
    navigate(`/chat/${id}`);
  };

  const handleConversationLanded = (id: string): void => {
    navigate(`/chat/${id}`, { replace: true });
  };

  return (
    <section
      className="flex h-[calc(100vh-8.5rem)] min-h-[28rem] flex-col gap-3"
      aria-label="Chat workspace"
    >
      <header className="space-y-1">
        <h1 className="text-xl font-semibold tracking-tight">Chat</h1>
        <p className="text-sm text-muted-foreground">
          Grounded answers with citations and retrieval evidence—not a free-form chat clone.
        </p>
      </header>

      {isReady ? (
        <ChatSessionPane
          key={paneKey}
          conversationId={activeId}
          initialRecord={record}
          conversations={conversations}
          save={save}
          remove={remove}
          refresh={refresh}
          onNavigateConversation={handleSelectConversation}
          onConversationLanded={handleConversationLanded}
          onNew={handleNew}
        />
      ) : (
        <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
          Loading conversation…
        </div>
      )}
    </section>
  );
}
