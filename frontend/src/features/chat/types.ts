/** Chat domain types mapped from ChatResponseDTO / RetrieveResponseDTO. */

/** Streaming-ready turn state (SSE not implemented yet). */
export type TurnStreamingState = "idle" | "pending" | "streaming" | "complete" | "error";

export type Citation = {
  readonly chunk_id: string;
  readonly document_id: string;
  readonly document_version_id: string;
  readonly rank: number;
  readonly relevance_score: number;
  readonly excerpt: string;
  readonly start_char: number | null;
  readonly end_char: number | null;
  readonly marker: string;
};

export type RetrievedChunk = {
  readonly chunk_id: string;
  readonly document_id: string;
  readonly document_version_id: string;
  readonly knowledge_base_id: string;
  readonly score: number;
  readonly text: string;
  readonly chunk_index: number;
  readonly start_char: number;
  readonly end_char: number;
  readonly heading: string | null;
  readonly language: string | null;
};

export type ChatResponse = {
  readonly conversation_id: string | null;
  readonly answer: string | null;
  readonly citations: readonly Citation[];
  readonly retrieved_chunks: readonly RetrievedChunk[];
  readonly abstained: boolean;
  readonly status: string;
  readonly abstention_reason: string | null;
  readonly failure_reason: string | null;
  readonly model_key: string | null;
  readonly prompt_template_version: string | null;
  readonly warnings: readonly string[];
};

export type RetrieveResponse = {
  readonly query: string;
  readonly knowledge_base_id: string;
  readonly embedding_model_id: string;
  readonly top_k: number;
  readonly results: readonly RetrievedChunk[];
  readonly result_count: number;
  readonly warnings: readonly string[];
};

export type ChatRequestInput = {
  readonly question: string;
  readonly knowledge_base_id: string;
  readonly conversation_id?: string | null;
  readonly top_k?: number | null;
  readonly language_hint?: string | null;
  readonly document_ids?: readonly string[] | null;
};

export type RetrieveRequestInput = {
  readonly query: string;
  readonly knowledge_base_id: string;
  readonly top_k?: number;
  readonly language?: string | null;
  readonly document_ids?: readonly string[] | null;
};

export type ChatMessage = {
  readonly id: string;
  readonly role: "user" | "assistant";
  readonly content: string;
  readonly createdAt: string;
  readonly streamingState: TurnStreamingState;
  readonly status?: string;
  readonly citations?: readonly Citation[];
  readonly retrievedChunks?: readonly RetrievedChunk[];
  readonly abstained?: boolean;
  readonly abstentionReason?: string | null;
  readonly failureReason?: string | null;
  readonly modelKey?: string | null;
  readonly promptTemplateVersion?: string | null;
  readonly warnings?: readonly string[];
  readonly clientLatencyMs?: number | null;
  /** Question that produced this assistant turn (for retry / pipeline). */
  readonly sourceQuestion?: string;
  readonly topK?: number;
};

export type ConversationSummary = {
  readonly id: string;
  readonly title: string;
  readonly knowledgeBaseId: string;
  readonly updatedAt: string;
};

export type ConversationRecord = ConversationSummary & {
  readonly messages: readonly ChatMessage[];
};
