import { Folder } from "lucide-react";
import * as React from "react";

import { Input } from "@/components/ui/input";
import { EmptyState } from "@/features/knowledge/components/empty-state";
import { StatusChip } from "@/features/knowledge/components/status-chip";
import { formatRelativeTime } from "@/features/knowledge/lib/format";
import type { DocumentSummary, FolderSummary } from "@/features/knowledge/types";
import { cn } from "@/lib/utils";

type DocumentListProps = {
  readonly folders: readonly FolderSummary[];
  readonly documents: readonly DocumentSummary[];
  readonly selectedDocumentId: string | null;
  readonly onSelectDocument: (documentId: string) => void;
  readonly onSelectFolder: (folderId: string) => void;
  readonly onUpload: () => void;
  readonly search: string;
  readonly onSearchChange: (value: string) => void;
};

export function DocumentList({
  folders,
  documents,
  selectedDocumentId,
  onSelectDocument,
  onSelectFolder,
  onUpload,
  search,
  onSearchChange,
}: DocumentListProps): React.JSX.Element {
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
              </tr>
            </thead>
            <tbody>
              {filteredFolders.map((folder) => (
                <tr
                  key={`folder-${folder.id}`}
                  className="cursor-pointer border-b border-border hover:bg-muted/40"
                  onClick={() => onSelectFolder(folder.id)}
                >
                  <td className="px-3 py-2 font-medium" colSpan={4}>
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
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
