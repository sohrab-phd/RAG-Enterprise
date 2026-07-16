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

type DeleteKnowledgeBaseDialogProps = {
  readonly open: boolean;
  readonly knowledgeBaseName: string;
  readonly pending: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly onConfirm: () => void;
};

export function DeleteKnowledgeBaseDialog({
  open,
  knowledgeBaseName,
  pending,
  onOpenChange,
  onConfirm,
}: DeleteKnowledgeBaseDialogProps): React.JSX.Element {
  return (
    <Dialog open={open} onOpenChange={(next) => (pending ? undefined : onOpenChange(next))}>
      <DialogContent aria-describedby="delete-kb-description">
        <DialogHeader>
          <DialogTitle>Delete Knowledge Base?</DialogTitle>
          <DialogDescription id="delete-kb-description">
            This operation is permanent. “{knowledgeBaseName}” and all related data will be removed.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3 text-sm text-muted-foreground">
          <p>The following will be removed:</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>Knowledge Base</li>
            <li>All uploaded documents</li>
            <li>All document versions</li>
            <li>All chunks</li>
            <li>All embeddings</li>
            <li>All indexing records</li>
            <li>Local uploaded files</li>
            <li>All metadata</li>
          </ul>
          <p className="font-medium text-destructive">This action cannot be undone.</p>
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
