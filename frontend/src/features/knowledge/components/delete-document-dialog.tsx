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

type DeleteDocumentDialogProps = {
  readonly open: boolean;
  readonly documentTitle: string;
  readonly pending: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly onConfirm: () => void;
};

export function DeleteDocumentDialog({
  open,
  documentTitle,
  pending,
  onOpenChange,
  onConfirm,
}: DeleteDocumentDialogProps): React.JSX.Element {
  return (
    <Dialog open={open} onOpenChange={(next) => (pending ? undefined : onOpenChange(next))}>
      <DialogContent aria-describedby="delete-document-description">
        <DialogHeader>
          <DialogTitle>Delete Document</DialogTitle>
          <DialogDescription id="delete-document-description">
            Are you sure you want to permanently delete: {documentTitle}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3 text-sm text-muted-foreground">
          <p>This action cannot be undone.</p>
          <p>This will permanently remove:</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>the document</li>
            <li>every version</li>
            <li>upload sessions</li>
            <li>all generated chunks</li>
            <li>all embeddings</li>
            <li>all indexing information</li>
            <li>storage files</li>
            <li>every database record related to this document</li>
          </ul>
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
