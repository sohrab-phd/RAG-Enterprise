import { apiRequest, workspacePath } from "@/lib/api/client";
import type {
  ChatRequestInput,
  ChatResponse,
  RetrieveRequestInput,
  RetrieveResponse,
} from "@/features/chat/types";

export function sendChatTurn(input: ChatRequestInput, signal?: AbortSignal): Promise<ChatResponse> {
  return apiRequest(workspacePath("/chat"), {
    method: "POST",
    body: {
      question: input.question,
      knowledge_base_id: input.knowledge_base_id,
      conversation_id: input.conversation_id ?? null,
      top_k: input.top_k ?? null,
      language_hint: input.language_hint ?? null,
      document_ids: input.document_ids ?? null,
    },
    signal,
    timeoutMs: 90_000,
  });
}

export function retrieveChunks(
  input: RetrieveRequestInput,
  signal?: AbortSignal,
): Promise<RetrieveResponse> {
  return apiRequest(workspacePath("/retrieve"), {
    method: "POST",
    body: {
      query: input.query,
      knowledge_base_id: input.knowledge_base_id,
      top_k: input.top_k ?? 8,
      language: input.language ?? null,
      document_ids: input.document_ids ?? null,
    },
    signal,
    timeoutMs: 60_000,
  });
}
