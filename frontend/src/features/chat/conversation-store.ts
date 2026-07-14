import type { ConversationRecord, ConversationSummary } from "@/features/chat/types";

const STORAGE_KEY = "rag-enterprise-chat-conversations-v1";

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.sessionStorage !== "undefined";
}

export function loadConversations(): ConversationRecord[] {
  if (!canUseStorage()) return [];
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ConversationRecord[];
    if (!Array.isArray(parsed)) return [];
    return parsed;
  } catch {
    return [];
  }
}

export function saveConversations(records: readonly ConversationRecord[]): void {
  if (!canUseStorage()) return;
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(records));
}

export function upsertConversation(record: ConversationRecord): ConversationRecord[] {
  const current = loadConversations();
  const index = current.findIndex((item) => item.id === record.id);
  const next =
    index >= 0 ? current.map((item, i) => (i === index ? record : item)) : [record, ...current];
  next.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
  saveConversations(next);
  return next;
}

export function deleteConversation(id: string): ConversationRecord[] {
  const next = loadConversations().filter((item) => item.id !== id);
  saveConversations(next);
  return next;
}

export function getConversation(id: string): ConversationRecord | undefined {
  return loadConversations().find((item) => item.id === id);
}

export function toSummaries(records: readonly ConversationRecord[]): ConversationSummary[] {
  return records.map(({ id, title, knowledgeBaseId, updatedAt }) => ({
    id,
    title,
    knowledgeBaseId,
    updatedAt,
  }));
}

export function titleFromQuestion(question: string): string {
  const trimmed = question.trim().replace(/\s+/g, " ");
  if (trimmed.length <= 48) return trimmed;
  return `${trimmed.slice(0, 45)}…`;
}
