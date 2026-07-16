import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Folder, Loader2, Trash2 } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { deleteDocument } from "@/features/knowledge/api";
import { DeleteDocumentDialog } from "@/features/knowledge/components/delete-document-dialog";
import { EmptyState } from "@/features/knowledge/components/empty-state";
import { StatusChip } from "@/features/knowledge/components/status-chip";
import { formatRelativeTime } from "@/features/knowledge/lib/format";
import { knowledgeKeys } from "@/features/knowledge/query-keys";
import type { DocumentSummary, FolderSummary } from "@/features/knowledge/types";
import { isApiError } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type DocumentListProps = {
  readonly knowledgeBaseId: string;
  readonly folders: readonly FolderSummary[];
  readonly documents: readonly DocumentSummary[];
  readonly selectedDocumentId: string | null;
  readonly onSelectDocument: (documentId: string) => void;
  readonly onSelectFolder: (folderId: string) => void;
  readonly onClearDocumentSelection: () => void;
  readonly onUpload: () => void;
  readonly search: string;
  readonly onSearchChange: (value: string) => void;
};

export function DocumentList({
  knowledgeBaseId,
  folders,
  documents,
  selectedDocumentId,
  onSelectDocument,
  onSelectFolder,
  onClearDocumentSelection,
  onUpload,
  search,
  onSearchChange,
}: DocumentListProps): React.JSX.Element {
  const queryClient = useQueryClient();
  const [deleteTarget, setDeleteTarget] = React.useState<{
    id: string;
    title: string;
  } | null>(null);
  const [deleteError, setDeleteError] = React.useState<string | null>(null);
  const [successToast, setSuccessToast] = React.useState<string | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (documentId: string) => deleteDocument(knowledgeBaseId, documentId),
    onMutate: () => {
      setDeleteError(null);
    },
    onSuccess: async (_data, documentId) => {
      const title = deleteTarget?.title ?? "Document";
      setDeleteTarget(null);
      if (selectedDocumentId === documentId) {
        onClearDocumentSelection();
      }
      setSuccessToast(`Deleted “${title}”`);
      await Promise.all([
        queryClient.invalidateQueries({
          predicate: (query) =>
            Array.isArray(query.queryKey) &&
            query.queryKey[0] === "knowledge" &&
            query.queryKey[1] === "contents" &&
            query.queryKey[2] === knowledgeBaseId,
        }),
        queryClient.invalidateQueries({ queryKey: knowledgeKeys.tree(knowledgeBaseId) }),
        queryClient.invalidateQueries({ queryKey: knowledgeKeys.baseDetail(knowledgeBaseId) }),
        queryClient.removeQueries({
          queryKey: knowledgeKeys.document(knowledgeBaseId, documentId),
        }),
        queryClient.removeQueries({
          queryKey: knowledgeKeys.lastVersion(knowledgeBaseId, documentId),
        }),
      ]);
      window.setTimeout(() => setSuccessToast(null), 4000);
    },
    onError: (error) => {
      setDeleteError(isApiError(error) ? error.message : "Delete failed");
    },
  });

  const q = search.trim().toLowerCase();
  const filteredFolders = q
    ? folders.filter((folder) => folder.name.toLowerCase().includes(q))
    : folders;
  const filteredDocuments = q
    ? documents.filter((doc) => doc.title.toLowerCase().includes(q))
    : documents;
  const empty = filteredFolders.length === 0 && filteredDocuments.length === 0;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b border-border p-3">
        <Input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search in this folder"
          aria-label="Search documents"
        />
      </div>
      {deleteError ? (
        <p className="border-b border-border px-3 py-2 text-sm text-destructive" role="alert">
          {deleteError}
        </p>
      ) : null}
      {successToast ? (
        <p className="border-b border-border px-3 py-2 text-sm text-foreground" role="status">
          {successToast}
        </p>
      ) : null}
      <div className="min-h-0 flex-1 overflow-auto">
        {empty ? (
          <div className="p-4">
            <EmptyState
              title="This folder has no documents"
              description="Upload a file or create a subfolder to get started."
              actionLabel="Upload"
              onAction={onUpload}
            />
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 bg-card">
              <tr className="border-b border-border text-muted-foreground">
                <th className="px-3 py-2 font-medium">Title</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="hidden px-3 py-2 font-medium sm:table-cell">Lang</th>
                <th className="hidden px-3 py-2 font-medium md:table-cell">Updated</th>
                <th className="px-3 py-2 font-medium">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredFolders.map((folder) => (
                <tr
                  key={`folder-${folder.id}`}
                  className="cursor-pointer border-b border-border hover:bg-muted/40"
                  onClick={() => onSelectFolder(folder.id)}
                >
                  <td className="px-3 py-2 font-medium" colSpan={5}>
                    <span className="inline-flex items-center gap-2">
                      <Folder className="size-4 text-muted-foreground" aria-hidden />
                      {folder.name}
                    </span>
                  </td>
                </tr>
              ))}
              {filteredDocuments.map((doc) => {
                const selected = selectedDocumentId === doc.id;
                return (
                  <tr
                    key={doc.id}
                    className={cn(
                      "cursor-pointer border-b border-border hover:bg-muted/40",
                      selected && "bg-muted/60",
                    )}
                    onClick={() => onSelectDocument(doc.id)}
                    aria-selected={selected}
                  >
                    <td className="px-3 py-2 font-medium">{doc.title}</td>
                    <td className="px-3 py-2">
                      <StatusChip status={doc.status} />
                    </td>
                    <td className="hidden px-3 py-2 text-muted-foreground sm:table-cell">
                      {doc.declared_language}
                    </td>
                    <td className="hidden px-3 py-2 text-muted-foreground md:table-cell">
                      {formatRelativeTime(doc.updated_at)}
                    </td>
                    <td className="px-3 py-2">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        aria-label={`Delete ${doc.title}`}
                        disabled={deleteMutation.isPending}
                        onClick={(event) => {
                          event.stopPropagation();
                          setDeleteError(null);
                          setDeleteTarget({ id: doc.id, title: doc.title });
                        }}
                      >
                        {deleteMutation.isPending && deleteTarget?.id === doc.id ? (
                          <Loader2 className="size-4 animate-spin" aria-hidden />
                        ) : (
                          <Trash2 className="size-4" aria-hidden />
                        )}
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <DeleteDocumentDialog
        open={deleteTarget !== null}
        documentTitle={deleteTarget?.title ?? ""}
        pending={deleteMutation.isPending}
        onOpenChange={(open) => {
          if (!open && !deleteMutation.isPending) {
            setDeleteTarget(null);
          }
        }}
        onConfirm={() => {
          if (deleteTarget) {
            deleteMutation.mutate(deleteTarget.id);
          }
        }}
      />
    </div>
  );
}
