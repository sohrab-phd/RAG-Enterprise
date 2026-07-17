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

type DeleteFolderDialogProps = {
  readonly open: boolean;
  readonly folderName: string;
  readonly pending: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly onConfirm: () => void;
};

export function DeleteFolderDialog({
  open,
  folderName,
  pending,
  onOpenChange,
  onConfirm,
}: DeleteFolderDialogProps): React.JSX.Element {
  return (
    <Dialog open={open} onOpenChange={(next) => (pending ? undefined : onOpenChange(next))}>
      <DialogContent aria-describedby="delete-folder-description">
        <DialogHeader>
          <DialogTitle>Delete Folder?</DialogTitle>
          <DialogDescription id="delete-folder-description">
            Folder: {folderName}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3 text-sm text-muted-foreground">
          <p>This permanently deletes:</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>the folder</li>
            <li>every document inside the folder</li>
            <li>every document version</li>
            <li>upload sessions</li>
            <li>chunks</li>
            <li>embeddings</li>
            <li>indexing records</li>
            <li>storage files</li>
            <li>every database record belonging to those documents</li>
          </ul>
          <p>This action cannot be undone.</p>
        </div>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            disabled={pending}
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            disabled={pending}
            onClick={onConfirm}
            aria-busy={pending}
          >
            {pending ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
