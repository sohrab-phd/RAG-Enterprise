import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";
import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { getFolderContents, getKnowledgeBase, getTree } from "@/features/knowledge/api";
import { CreateFolderDialog } from "@/features/knowledge/components/create-folder-dialog";
import { DocumentInspector } from "@/features/knowledge/components/document-inspector";
import { DocumentList } from "@/features/knowledge/components/document-list";
import { EmptyState } from "@/features/knowledge/components/empty-state";
import { ErrorState } from "@/features/knowledge/components/error-state";
import { FolderTree } from "@/features/knowledge/components/folder-tree";
import { TableSkeleton, TreeSkeleton } from "@/features/knowledge/components/skeletons";
import { UploadDrawer } from "@/features/knowledge/components/upload-drawer";
import { knowledgeKeys } from "@/features/knowledge/query-keys";
import type { TreeFolderNode } from "@/features/knowledge/types";
import { cn } from "@/lib/utils";

function findFolderPath(folders: readonly TreeFolderNode[], folderId: string | null): string {
  if (!folderId) return "Root";
  const path: string[] = [];

  const walk = (nodes: readonly TreeFolderNode[], trail: string[]): boolean => {
    for (const node of nodes) {
      const next = [...trail, node.name];
      if (node.id === folderId) {
        path.push(...next);
        return true;
      }
      if (walk(node.children, next)) return true;
    }
    return false;
  };

  walk(folders, []);
  return path.length > 0 ? path.join(" / ") : "Folder";
}

export function KnowledgeBrowser(): React.JSX.Element {
  const { kbId = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const folderId = searchParams.get("folderId");
  const documentId = searchParams.get("documentId");
  const [listSearch, setListSearch] = React.useState("");
  const [uploadOpen, setUploadOpen] = React.useState(false);
  const [folderOpen, setFolderOpen] = React.useState(false);
  const [mobilePane, setMobilePane] = React.useState<"tree" | "list" | "detail">("list");

  const kbQuery = useQuery({
    queryKey: knowledgeKeys.baseDetail(kbId),
    queryFn: ({ signal }) => getKnowledgeBase(kbId, signal),
    enabled: Boolean(kbId),
  });

  const treeQuery = useQuery({
    queryKey: knowledgeKeys.tree(kbId),
    queryFn: ({ signal }) => getTree(kbId, { depth: 10, signal }),
    enabled: Boolean(kbId),
  });

  const contentsQuery = useQuery({
    queryKey: knowledgeKeys.contents(kbId, folderId, 1, 50),
    queryFn: ({ signal }) =>
      getFolderContents(kbId, {
        folderId,
        page: 1,
        pageSize: 50,
        signal,
      }),
    enabled: Boolean(kbId),
  });

  const setSelection = (next: { folderId?: string | null; documentId?: string | null }): void => {
    const params = new URLSearchParams(searchParams);
    if ("folderId" in next) {
      if (next.folderId) params.set("folderId", next.folderId);
      else params.delete("folderId");
      params.delete("documentId");
    }
    if ("documentId" in next) {
      if (next.documentId) params.set("documentId", next.documentId);
      else params.delete("documentId");
    }
    setSearchParams(params);
  };

  if (!kbId) {
    return <EmptyState title="Missing knowledge base" />;
  }

  if (kbQuery.isError) {
    return (
      <ErrorState
        error={kbQuery.error}
        onRetry={() => void kbQuery.refetch()}
        title="Unable to load knowledge base"
      />
    );
  }

  const folderLabel = findFolderPath(treeQuery.data?.folders ?? [], folderId);

  return (
    <section className="flex h-full min-h-0 flex-col gap-4">
      <PageHeader
        title={kbQuery.data?.name ?? "Knowledge base"}
        description="Browse folders, upload documents, and inspect processing status."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" asChild>
              <Link to="/knowledge">All knowledge bases</Link>
            </Button>
            <Button type="button" variant="outline" onClick={() => setFolderOpen(true)}>
              New folder
            </Button>
            <Button type="button" onClick={() => setUploadOpen(true)}>
              Upload
            </Button>
          </div>
        }
      />

      <div className="flex gap-2 lg:hidden">
        {(
          [
            ["tree", "Tree"],
            ["list", "Documents"],
            ["detail", "Detail"],
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

      <div className="grid min-h-[28rem] flex-1 grid-cols-1 overflow-hidden rounded-lg border border-border bg-card lg:grid-cols-[240px_minmax(0,1fr)_320px] xl:grid-cols-[260px_minmax(0,1fr)_360px]">
        <aside
          className={cn(
            "min-h-0 overflow-auto border-b border-border p-3 lg:border-b-0 lg:border-r",
            mobilePane === "tree" ? "block" : "hidden lg:block",
          )}
          aria-label="Folder tree"
        >
          {treeQuery.isLoading ? <TreeSkeleton /> : null}
          {treeQuery.isError ? (
            <ErrorState error={treeQuery.error} onRetry={() => void treeQuery.refetch()} />
          ) : null}
          {treeQuery.data ? (
            <FolderTree
              folders={treeQuery.data.folders}
              selectedFolderId={folderId}
              onSelectFolder={(id) => {
                setSelection({ folderId: id });
                setMobilePane("list");
              }}
            />
          ) : null}
        </aside>

        <div
          className={cn(
            "min-h-0 border-b border-border lg:border-b-0 lg:border-r",
            mobilePane === "list" ? "block" : "hidden lg:block",
          )}
        >
          <div className="border-b border-border px-3 py-2 text-xs text-muted-foreground">
            Folder: {folderLabel}
          </div>
          {contentsQuery.isLoading ? (
            <div className="p-3">
              <TableSkeleton rows={6} />
            </div>
          ) : null}
          {contentsQuery.isError ? (
            <div className="p-3">
              <ErrorState
                error={contentsQuery.error}
                onRetry={() => void contentsQuery.refetch()}
              />
            </div>
          ) : null}
          {contentsQuery.data ? (
            <DocumentList
              knowledgeBaseId={kbId}
              folders={contentsQuery.data.folders}
              documents={contentsQuery.data.documents}
              selectedDocumentId={documentId}
              search={listSearch}
              onSearchChange={setListSearch}
              onUpload={() => setUploadOpen(true)}
              onSelectFolder={(id) => {
                setSelection({ folderId: id });
              }}
              onSelectDocument={(id) => {
                setSelection({ documentId: id });
                setMobilePane("detail");
              }}
              onClearDocumentSelection={() => {
                setSelection({ documentId: null });
              }}
            />
          ) : null}
        </div>

        <aside
          className={cn(
            "min-h-0 overflow-auto",
            mobilePane === "detail" ? "block" : "hidden lg:block",
          )}
          aria-label="Document detail"
        >
          <DocumentInspector knowledgeBaseId={kbId} documentId={documentId} />
        </aside>
      </div>

      <UploadDrawer
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        knowledgeBaseId={kbId}
        folderId={folderId}
        folderLabel={folderLabel}
      />
      <CreateFolderDialog
        open={folderOpen}
        onOpenChange={setFolderOpen}
        knowledgeBaseId={kbId}
        parentFolderId={folderId}
      />
    </section>
  );
}
