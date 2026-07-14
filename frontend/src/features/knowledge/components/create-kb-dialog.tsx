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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { createKnowledgeBase } from "@/features/knowledge/api";
import { knowledgeKeys } from "@/features/knowledge/query-keys";
import { isApiError } from "@/lib/api/types";

const schema = z.object({
  name: z.string().trim().min(1, "Name is required").max(200),
  default_language: z.string().min(1),
  visibility_policy: z.string().min(1),
  description: z.string().max(2000).optional(),
});

type FormValues = z.infer<typeof schema>;

type CreateKnowledgeBaseDialogProps = {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly onCreated?: (id: string) => void;
};

export function CreateKnowledgeBaseDialog({
  open,
  onOpenChange,
  onCreated,
}: CreateKnowledgeBaseDialogProps): React.JSX.Element {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      default_language: "en",
      visibility_policy: "workspace",
      description: "",
    },
  });

  const mutation = useMutation({
    mutationFn: createKnowledgeBase,
    onSuccess: async (data) => {
      await queryClient.invalidateQueries({ queryKey: knowledgeKeys.bases() });
      reset();
      onOpenChange(false);
      onCreated?.(data.id);
    },
    onError: (error) => {
      if (isApiError(error) && error.code === "conflict") {
        setError("name", { message: error.message });
        return;
      }
      setError("root", {
        message: isApiError(error) ? error.message : "Failed to create",
      });
    },
  });

  const onSubmit = handleSubmit((values) => {
    mutation.mutate({
      name: values.name,
      default_language: values.default_language,
      visibility_policy: values.visibility_policy,
      description: values.description?.trim() || null,
    });
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby={undefined}>
        <DialogHeader>
          <DialogTitle>Create knowledge base</DialogTitle>
          <DialogDescription>
            Add a curated corpus for documents, retrieval, and evaluation.
          </DialogDescription>
        </DialogHeader>
        <form className="space-y-4" onSubmit={onSubmit} noValidate>
          <div className="space-y-2">
            <Label htmlFor="kb-name">Name</Label>
            <Input id="kb-name" autoFocus {...register("name")} />
            {errors.name ? <p className="text-xs text-destructive">{errors.name.message}</p> : null}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="kb-language">Default language</Label>
              <Select
                value={watch("default_language")}
                onValueChange={(value) =>
                  setValue("default_language", value, { shouldValidate: true })
                }
              >
                <SelectTrigger id="kb-language" aria-label="Default language">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="en">en</SelectItem>
                  <SelectItem value="fa">fa</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="kb-visibility">Visibility</Label>
              <Select
                value={watch("visibility_policy")}
                onValueChange={(value) =>
                  setValue("visibility_policy", value, { shouldValidate: true })
                }
              >
                <SelectTrigger id="kb-visibility" aria-label="Visibility">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="private">private</SelectItem>
                  <SelectItem value="workspace">workspace</SelectItem>
                  <SelectItem value="organization">organization</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="kb-description">Description</Label>
            <Textarea id="kb-description" rows={3} {...register("description")} />
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
            <Button type="submit" disabled={isSubmitting || mutation.isPending}>
              {mutation.isPending ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
