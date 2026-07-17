import { ChevronDown, ChevronRight, Folder, Loader2, Trash2 } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import type { TreeFolderNode } from "@/features/knowledge/types";
import { cn } from "@/lib/utils";

type FolderTreeProps = {
  readonly folders: readonly TreeFolderNode[];
  readonly selectedFolderId: string | null;
  readonly onSelectFolder: (folderId: string | null) => void;
  readonly onRequestDeleteFolder?: (folderId: string, folderName: string) => void;
  readonly deletingFolderId?: string | null;
  readonly deletePending?: boolean;
};

type NodeProps = {
  readonly node: TreeFolderNode;
  readonly depth: number;
  readonly selectedFolderId: string | null;
  readonly onSelectFolder: (folderId: string | null) => void;
  readonly onRequestDeleteFolder?: (folderId: string, folderName: string) => void;
  readonly deletingFolderId?: string | null;
  readonly deletePending?: boolean;
};

function TreeNode({
  node,
  depth,
  selectedFolderId,
  onSelectFolder,
  onRequestDeleteFolder,
  deletingFolderId,
  deletePending,
}: NodeProps): React.JSX.Element {
  const [expanded, setExpanded] = React.useState(depth < 2);
  const hasChildren = node.children.length > 0;
  const selected = selectedFolderId === node.id;
  const isDeleting = deletePending && deletingFolderId === node.id;

  return (
    <li>
      <div
        className={cn(
          "group flex w-full items-center gap-1 rounded-md text-sm",
          selected && "bg-sidebar-accent text-sidebar-accent-foreground",
        )}
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
      >
        <button
          type="button"
          className="flex size-7 items-center justify-center rounded-sm text-muted-foreground hover:bg-muted"
          aria-label={expanded ? `Collapse ${node.name}` : `Expand ${node.name}`}
          aria-expanded={hasChildren ? expanded : undefined}
          disabled={!hasChildren}
          onClick={() => setExpanded((value) => !value)}
        >
          {hasChildren ? (
            expanded ? (
              <ChevronDown className="size-4" aria-hidden />
            ) : (
              <ChevronRight className="size-4" aria-hidden />
            )
          ) : (
            <span className="size-4" aria-hidden />
          )}
        </button>
        <button
          type="button"
          className="flex min-w-0 flex-1 items-center gap-2 px-1 py-1.5 text-left hover:bg-muted/60"
          onClick={() => onSelectFolder(node.id)}
          aria-current={selected ? "true" : undefined}
        >
          <Folder className="size-4 shrink-0 text-muted-foreground" aria-hidden />
          <span className="truncate font-medium">{node.name}</span>
          <span className="ml-auto shrink-0 text-xs text-muted-foreground tabular-nums">
            {node.document_count}
          </span>
        </button>
        {onRequestDeleteFolder ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-7 shrink-0 opacity-70 group-hover:opacity-100"
            aria-label={`Delete folder ${node.name}`}
            disabled={deletePending}
            onClick={(event) => {
              event.stopPropagation();
              onRequestDeleteFolder(node.id, node.name);
            }}
          >
            {isDeleting ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <Trash2 className="size-4" aria-hidden />
            )}
          </Button>
        ) : null}
      </div>
      {hasChildren && expanded ? (
        <ul className="space-y-0.5">
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedFolderId={selectedFolderId}
              onSelectFolder={onSelectFolder}
              onRequestDeleteFolder={onRequestDeleteFolder}
              deletingFolderId={deletingFolderId}
              deletePending={deletePending}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

export function FolderTree({
  folders,
  selectedFolderId,
  onSelectFolder,
  onRequestDeleteFolder,
  deletingFolderId,
  deletePending,
}: FolderTreeProps): React.JSX.Element {
  return (
    <div className="space-y-1">
      <button
        type="button"
        className={cn(
          "flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm font-medium hover:bg-muted/60",
          selectedFolderId === null && "bg-sidebar-accent text-sidebar-accent-foreground",
        )}
        onClick={() => onSelectFolder(null)}
        aria-current={selectedFolderId === null ? "true" : undefined}
      >
        <Folder className="size-4" aria-hidden />
        Root
      </button>
      <ul className="space-y-0.5">
        {folders.map((node) => (
          <TreeNode
            key={node.id}
            node={node}
            depth={0}
            selectedFolderId={selectedFolderId}
            onSelectFolder={onSelectFolder}
            onRequestDeleteFolder={onRequestDeleteFolder}
            deletingFolderId={deletingFolderId}
            deletePending={deletePending}
          />
        ))}
      </ul>
    </div>
  );
}
