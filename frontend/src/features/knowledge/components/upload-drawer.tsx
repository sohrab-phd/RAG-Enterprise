import { useQueryClient } from "@tanstack/react-query";
import { FileUp, X } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import {
  completeUpload,
  createDocument,
  createDocumentVersion,
  initiateUpload,
} from "@/features/knowledge/api";
import { formatBytes, isAcceptedFile } from "@/features/knowledge/lib/format";
import { knowledgeKeys } from "@/features/knowledge/query-keys";
import type { DocumentVersionSummary } from "@/features/knowledge/types";
import { isApiError } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type UploadRowStatus = "queued" | "uploading" | "completed" | "failed" | "cancelled";

type UploadRow = {
  readonly id: string;
  readonly file: File;
  status: UploadRowStatus;
  progress: number;
  error?: string;
  documentId?: string;
  version?: DocumentVersionSummary;
};

type UploadDrawerProps = {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly knowledgeBaseId: string;
  readonly folderId: string | null;
  readonly folderLabel: string;
};

function createRowId(): string {
  return crypto.randomUUID();
}

export function UploadDrawer({
  open,
  onOpenChange,
  knowledgeBaseId,
  folderId,
  folderLabel,
}: UploadDrawerProps): React.JSX.Element {
  const queryClient = useQueryClient();
  const [rows, setRows] = React.useState<UploadRow[]>([]);
  const [dragging, setDragging] = React.useState(false);
  const [running, setRunning] = React.useState(false);
  const abortRef = React.useRef<AbortController | null>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const updateRow = React.useCallback((id: string, patch: Partial<UploadRow>) => {
    setRows((current) => current.map((row) => (row.id === id ? { ...row, ...patch } : row)));
  }, []);

  const addFiles = React.useCallback((fileList: FileList | File[]) => {
    const next: UploadRow[] = [];
    for (const file of Array.from(fileList)) {
      if (!isAcceptedFile(file)) {
        next.push({
          id: createRowId(),
          file,
          status: "failed",
          progress: 0,
          error: "Unsupported file type",
        });
        continue;
      }
      next.push({
        id: createRowId(),
        file,
        status: "queued",
        progress: 0,
      });
    }
    setRows((current) => [...current, ...next]);
  }, []);

  const cancelAll = (): void => {
    abortRef.current?.abort();
    setRows((current) =>
      current.map((row) =>
        row.status === "queued" || row.status === "uploading"
          ? { ...row, status: "cancelled", error: "Cancelled" }
          : row,
      ),
    );
    setRunning(false);
  };

  const uploadOne = async (row: UploadRow, signal: AbortSignal): Promise<void> => {
    updateRow(row.id, { status: "uploading", progress: 5, error: undefined });
    try {
      const document = await createDocument(knowledgeBaseId, {
        title: row.file.name,
        folder_id: folderId,
      });
      updateRow(row.id, { documentId: document.id, progress: 15 });

      const session = await initiateUpload(knowledgeBaseId, {
        file_name: row.file.name,
        file_size_bytes: row.file.size,
        mime_type: row.file.type || null,
        document_id: document.id,
      });
      updateRow(row.id, { progress: 25 });

      await completeUpload(knowledgeBaseId, session.id, row.file, {
        signal,
        onProgress: (loaded, total) => {
          const ratio = total > 0 ? loaded / total : 0;
          updateRow(row.id, {
            progress: Math.min(90, Math.round(25 + ratio * 65)),
          });
        },
      });
      updateRow(row.id, { progress: 92 });

      const version = await createDocumentVersion(knowledgeBaseId, document.id, session.id);
      queryClient.setQueryData(knowledgeKeys.lastVersion(knowledgeBaseId, document.id), version);
      updateRow(row.id, {
        status: "completed",
        progress: 100,
        version,
      });
    } catch (error) {
      if (signal.aborted) {
        updateRow(row.id, { status: "cancelled", error: "Cancelled" });
        return;
      }
      updateRow(row.id, {
        status: "failed",
        error: isApiError(error) ? error.message : "Upload failed",
      });
    }
  };

  const startUploads = async (): Promise<void> => {
    const queued = rows.filter((row) => row.status === "queued");
    if (queued.length === 0 || running) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setRunning(true);
    for (const row of queued) {
      if (controller.signal.aborted) break;
      await uploadOne(row, controller.signal);
    }
    setRunning(false);
    await queryClient.invalidateQueries({
      queryKey: knowledgeKeys.tree(knowledgeBaseId),
    });
    await queryClient.invalidateQueries({
      queryKey: [...knowledgeKeys.all, "contents", knowledgeBaseId],
    });
  };

  const allTerminal =
    rows.length > 0 &&
    rows.every(
      (row) => row.status === "completed" || row.status === "failed" || row.status === "cancelled",
    );

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (running && !next) return;
        if (!next) {
          setRows([]);
        }
        onOpenChange(next);
      }}
    >
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Upload documents</DialogTitle>
          <DialogDescription>Upload to: {folderLabel}</DialogDescription>
        </DialogHeader>

        <div
          className={cn(
            "flex min-h-36 flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-muted/20 p-6 text-center",
            dragging && "border-primary bg-primary/5",
          )}
          onDragEnter={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            if (event.dataTransfer.files.length > 0) {
              addFiles(event.dataTransfer.files);
            }
          }}
        >
          <FileUp className="size-8 text-muted-foreground" aria-hidden />
          <p className="text-sm text-foreground">
            Drop files here or{" "}
            <button
              type="button"
              className="font-medium underline-offset-2 hover:underline"
              onClick={() => inputRef.current?.click()}
            >
              browse
            </button>
          </p>
          <p className="text-xs text-muted-foreground">PDF, DOCX, TXT, MD, HTML</p>
          <input
            ref={inputRef}
            type="file"
            className="sr-only"
            multiple
            accept=".pdf,.docx,.doc,.txt,.md,.html,application/pdf,text/plain,text/markdown,text/html"
            onChange={(event) => {
              if (event.target.files) addFiles(event.target.files);
              event.target.value = "";
            }}
          />
        </div>

        {rows.length > 0 ? (
          <ul className="max-h-56 space-y-3 overflow-auto">
            {rows.map((row) => (
              <li key={row.id} className="rounded-md border border-border p-3 text-sm">
                <div className="mb-2 flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p
                      className={cn(
                        "truncate font-medium",
                        row.status === "cancelled" && "text-muted-foreground line-through",
                      )}
                    >
                      {row.file.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatBytes(row.file.size)} · {row.status}
                      {row.error ? ` · ${row.error}` : ""}
                    </p>
                  </div>
                  {(row.status === "queued" || row.status === "failed") && !running ? (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label={`Remove ${row.file.name}`}
                      onClick={() =>
                        setRows((current) => current.filter((item) => item.id !== row.id))
                      }
                    >
                      <X className="size-4" />
                    </Button>
                  ) : null}
                </div>
                <Progress value={row.progress} aria-label="Upload progress" />
              </li>
            ))}
          </ul>
        ) : null}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={cancelAll} disabled={!running}>
            Cancel all
          </Button>
          {!allTerminal ? (
            <Button
              type="button"
              onClick={() => void startUploads()}
              disabled={running || rows.every((row) => row.status !== "queued")}
            >
              {running ? "Uploading…" : "Start upload"}
            </Button>
          ) : (
            <Button
              type="button"
              onClick={() => {
                setRows([]);
                onOpenChange(false);
              }}
            >
              Done
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
