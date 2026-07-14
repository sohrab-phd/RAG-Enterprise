export type KnowledgeBaseSummary = {
  readonly id: string;
  readonly name: string;
  readonly status: string;
  readonly default_language: string;
  readonly visibility_policy: string;
  readonly document_count: number;
  readonly created_at: string;
  readonly updated_at: string;
};

export type KnowledgeBaseDetail = KnowledgeBaseSummary & {
  readonly description: string | null;
  readonly version: number;
};

export type FolderSummary = {
  readonly id: string;
  readonly name: string;
  readonly parent_folder_id: string | null;
  readonly path: string;
  readonly depth: number;
  readonly status: string;
  readonly version: number;
};

export type TreeFolderNode = {
  readonly id: string;
  readonly name: string;
  readonly status: string;
  readonly document_count: number;
  readonly children: readonly TreeFolderNode[];
};

export type TreeView = {
  readonly knowledge_base_id: string;
  readonly folders: readonly TreeFolderNode[];
};

export type DocumentSummary = {
  readonly id: string;
  readonly title: string;
  readonly status: string;
  readonly folder_id: string | null;
  readonly declared_language: string;
  readonly classification_label: string;
  readonly current_version_id: string | null;
  readonly updated_at: string;
};

export type DocumentDetail = DocumentSummary & {
  readonly source_type: string;
  readonly tags: readonly string[];
  readonly metadata: Readonly<Record<string, unknown>>;
  readonly legal_hold: boolean;
  readonly version: number;
  readonly created_at: string;
};

export type DocumentVersionSummary = {
  readonly id: string;
  readonly version_number: number;
  readonly extraction_method: string;
  readonly processing_status: string;
  readonly content_hash: string;
  readonly file_name: string;
  readonly file_size_bytes: number;
  readonly mime_type: string;
  readonly is_current: boolean;
  readonly created_at: string;
};

export type UploadSession = {
  readonly id: string;
  readonly status: string;
  readonly file_name: string;
  readonly file_size_bytes: number;
  readonly expires_at: string;
};

export type FolderContents = {
  readonly folder_id: string | null;
  readonly folders: readonly FolderSummary[];
  readonly documents: readonly DocumentSummary[];
  readonly pagination: {
    readonly page: number;
    readonly page_size: number;
    readonly total_items: number;
    readonly total_pages: number;
    readonly has_next: boolean;
    readonly has_previous: boolean;
  } | null;
};

export type CreateKnowledgeBaseInput = {
  readonly name: string;
  readonly default_language?: string;
  readonly visibility_policy?: string;
  readonly description?: string | null;
};

export type CreateFolderInput = {
  readonly name: string;
  readonly parent_folder_id?: string | null;
};

export type CreateDocumentInput = {
  readonly title: string;
  readonly folder_id?: string | null;
  readonly declared_language?: string | null;
  readonly source_type?: string;
  readonly classification_label?: string;
  readonly tags?: readonly string[];
  readonly metadata?: Readonly<Record<string, unknown>>;
};

export type UpdateDocumentInput = {
  readonly title?: string;
  readonly declared_language?: string | null;
  readonly classification_label?: string | null;
  readonly tags?: readonly string[];
  readonly metadata?: Readonly<Record<string, unknown>>;
  readonly expected_version?: number | null;
};

export type InitiateUploadInput = {
  readonly file_name: string;
  readonly file_size_bytes: number;
  readonly mime_type?: string | null;
  readonly document_id?: string | null;
  readonly checksum_sha256?: string | null;
};
