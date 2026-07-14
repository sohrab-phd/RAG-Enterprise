import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createFolder } from "@/features/knowledge/api";
import { knowledgeKeys } from "@/features/knowledge/query-keys";
import { isApiError } from "@/lib/api/types";

const schema = z.object({
  name: z.string().trim().min(1, "Name is required").max(200),
});

type FormValues = z.infer<typeof schema>;

type CreateFolderDialogProps = {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly knowledgeBaseId: string;
  readonly parentFolderId: string | null;
};

export function CreateFolderDialog({
  open,
  onOpenChange,
  knowledgeBaseId,
  parentFolderId,
}: CreateFolderDialogProps): React.JSX.Element {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "" },
  });

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      createFolder(knowledgeBaseId, {
        name: values.name,
        parent_folder_id: parentFolderId,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: knowledgeKeys.tree(knowledgeBaseId),
      });
      await queryClient.invalidateQueries({
        queryKey: [...knowledgeKeys.all, "contents", knowledgeBaseId],
      });
      reset();
      onOpenChange(false);
    },
    onError: (error) => {
      if (isApiError(error) && error.code === "conflict") {
        setError("name", { message: error.message });
        return;
      }
      setError("root", {
        message: isApiError(error) ? error.message : "Failed to create folder",
      });
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create folder</DialogTitle>
          <DialogDescription>
            {parentFolderId
              ? "Create a subfolder under the selected folder."
              : "Create a folder at the knowledge base root."}
          </DialogDescription>
        </DialogHeader>
        <form
          className="space-y-4"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <div className="space-y-2">
            <Label htmlFor="folder-name">Name</Label>
            <Input id="folder-name" autoFocus {...register("name")} />
            {errors.name ? <p className="text-xs text-destructive">{errors.name.message}</p> : null}
          </div>
          {errors.root ? (
            <p className="text-sm text-destructive" role="alert">
              {errors.root.message}
            </p>
          ) : null}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
