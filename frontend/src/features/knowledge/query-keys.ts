export const knowledgeKeys = {
  all: ["knowledge"] as const,
  bases: () => [...knowledgeKeys.all, "bases"] as const,
  baseList: (filters: {
    readonly page: number;
    readonly pageSize: number;
    readonly status?: string;
    readonly q?: string;
  }) => [...knowledgeKeys.bases(), "list", filters] as const,
  baseDetail: (id: string) => [...knowledgeKeys.bases(), "detail", id] as const,
  tree: (kbId: string) => [...knowledgeKeys.all, "tree", kbId] as const,
  contents: (kbId: string, folderId: string | null, page: number, pageSize: number) =>
    [...knowledgeKeys.all, "contents", kbId, folderId, page, pageSize] as const,
  document: (kbId: string, documentId: string) =>
    [...knowledgeKeys.all, "document", kbId, documentId] as const,
  lastVersion: (kbId: string, documentId: string) =>
    [...knowledgeKeys.all, "last-version", kbId, documentId] as const,
};
