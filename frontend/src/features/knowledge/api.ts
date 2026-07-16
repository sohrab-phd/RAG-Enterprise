import {
  apiRequest,
  apiUploadBinary,
  workspacePath,
  type UploadProgressHandler,
} from "@/lib/api/client";
import type { PaginatedData } from "@/lib/api/types";
import type {
  CreateDocumentInput,
  CreateFolderInput,
  CreateKnowledgeBaseInput,
  DocumentDetail,
  DocumentVersionSummary,
  FolderContents,
  FolderSummary,
  InitiateUploadInput,
  KnowledgeBaseDetail,
  KnowledgeBaseSummary,
  ProcessAndIndexResult,
  TreeView,
  UpdateDocumentInput,
  UploadSession,
} from "@/features/knowledge/types";

export function listKnowledgeBases(params: {
  readonly page?: number;
  readonly pageSize?: number;
  readonly status?: string;
  readonly q?: string;
  readonly signal?: AbortSignal;
}): Promise<PaginatedData<KnowledgeBaseSummary>> {
  const search = new URLSearchParams();
  search.set("page", String(params.page ?? 1));
  search.set("page_size", String(params.pageSize ?? 20));
  if (params.status) search.set("status", params.status);
  if (params.q) search.set("q", params.q);
  return apiRequest(workspacePath(`/knowledge-bases?${search.toString()}`), {
    signal: params.signal,
  });
}

export function getKnowledgeBase(
  knowledgeBaseId: string,
  signal?: AbortSignal,
): Promise<KnowledgeBaseDetail> {
  return apiRequest(workspacePath(`/knowledge-bases/${knowledgeBaseId}`), { signal });
}

export function createKnowledgeBase(input: CreateKnowledgeBaseInput): Promise<KnowledgeBaseDetail> {
  return apiRequest(workspacePath("/knowledge-bases"), {
    method: "POST",
    body: input,
  });
}

export function publishKnowledgeBase(knowledgeBaseId: string): Promise<KnowledgeBaseDetail> {
  return apiRequest(workspacePath(`/knowledge-bases/${knowledgeBaseId}/publish`), {
    method: "POST",
  });
}

export function deleteKnowledgeBase(knowledgeBaseId: string): Promise<void> {
  return apiRequest(workspacePath(`/knowledge-bases/${knowledgeBaseId}`), {
    method: "DELETE",
  });
}

export function getTree(
  knowledgeBaseId: string,
  params: { readonly depth?: number; readonly signal?: AbortSignal } = {},
): Promise<TreeView> {
  const search = new URLSearchParams();
  search.set("depth", String(params.depth ?? 10));
  return apiRequest(
    workspacePath(`/knowledge-bases/${knowledgeBaseId}/tree?${search.toString()}`),
    { signal: params.signal },
  );
}

export function getFolderContents(
  knowledgeBaseId: string,
  params: {
    readonly folderId?: string | null;
    readonly page?: number;
    readonly pageSize?: number;
    readonly signal?: AbortSignal;
  } = {},
): Promise<FolderContents> {
  const search = new URLSearchParams();
  search.set("page", String(params.page ?? 1));
  search.set("page_size", String(params.pageSize ?? 50));
  if (params.folderId) search.set("folder_id", params.folderId);
  return apiRequest(
    workspacePath(`/knowledge-bases/${knowledgeBaseId}/contents?${search.toString()}`),
    { signal: params.signal },
  );
}

export function createFolder(
  knowledgeBaseId: string,
  input: CreateFolderInput,
): Promise<FolderSummary> {
  return apiRequest(workspacePath(`/knowledge-bases/${knowledgeBaseId}/folders`), {
    method: "POST",
    body: input,
  });
}

export function createDocument(
  knowledgeBaseId: string,
  input: CreateDocumentInput,
): Promise<DocumentDetail> {
  return apiRequest(workspacePath(`/knowledge-bases/${knowledgeBaseId}/documents`), {
    method: "POST",
    body: input,
  });
}

export function getDocument(
  knowledgeBaseId: string,
  documentId: string,
  signal?: AbortSignal,
): Promise<DocumentDetail> {
  return apiRequest(workspacePath(`/knowledge-bases/${knowledgeBaseId}/documents/${documentId}`), {
    signal,
  });
}

export function updateDocument(
  knowledgeBaseId: string,
  documentId: string,
  input: UpdateDocumentInput,
): Promise<DocumentDetail> {
  return apiRequest(workspacePath(`/knowledge-bases/${knowledgeBaseId}/documents/${documentId}`), {
    method: "PATCH",
    body: input,
  });
}

export function initiateUpload(
  knowledgeBaseId: string,
  input: InitiateUploadInput,
): Promise<UploadSession> {
  return apiRequest(workspacePath(`/knowledge-bases/${knowledgeBaseId}/uploads`), {
    method: "POST",
    body: input,
  });
}

export function completeUpload(
  knowledgeBaseId: string,
  uploadId: string,
  content: Blob,
  options: {
    readonly signal?: AbortSignal;
    readonly onProgress?: UploadProgressHandler;
  } = {},
): Promise<UploadSession> {
  return apiUploadBinary(
    workspacePath(`/knowledge-bases/${knowledgeBaseId}/uploads/${uploadId}/complete`),
    content,
    options,
  );
}

export function createDocumentVersion(
  knowledgeBaseId: string,
  documentId: string,
  uploadId: string,
  changeSummary?: string,
): Promise<DocumentVersionSummary> {
  return apiRequest(
    workspacePath(`/knowledge-bases/${knowledgeBaseId}/documents/${documentId}/versions`),
    {
      method: "POST",
      body: {
        upload_id: uploadId,
        ...(changeSummary ? { change_summary: changeSummary } : {}),
      },
    },
  );
}

export function processAndIndexDocument(
  documentId: string,
  signal?: AbortSignal,
): Promise<ProcessAndIndexResult> {
  return apiRequest(workspacePath(`/documents/${documentId}/process`), {
    method: "POST",
    signal,
    timeoutMs: 120_000,
  });
}
