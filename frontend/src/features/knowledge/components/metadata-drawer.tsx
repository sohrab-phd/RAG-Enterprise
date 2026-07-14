import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { useFieldArray, useForm } from "react-hook-form";
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
import { updateDocument } from "@/features/knowledge/api";
import { knowledgeKeys } from "@/features/knowledge/query-keys";
import type { DocumentDetail } from "@/features/knowledge/types";
import { isApiError } from "@/lib/api/types";

const schema = z.object({
  title: z.string().trim().min(1).max(500),
  declared_language: z.string().min(1),
  classification_label: z.string().min(1),
  tags: z.string(),
  metadataEntries: z.array(
    z.object({
      key: z.string(),
      value: z.string(),
    }),
  ),
});

type FormValues = z.infer<typeof schema>;

type MetadataDrawerProps = {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly knowledgeBaseId: string;
  readonly document: DocumentDetail;
};

function metadataToEntries(
  metadata: Readonly<Record<string, unknown>>,
): FormValues["metadataEntries"] {
  return Object.entries(metadata).map(([key, value]) => ({
    key,
    value: typeof value === "string" ? value : JSON.stringify(value),
  }));
}

export function MetadataDrawer({
  open,
  onOpenChange,
  knowledgeBaseId,
  document,
}: MetadataDrawerProps): React.JSX.Element {
  const queryClient = useQueryClient();
  const readOnly = document.status === "archived" || document.status === "deleted";

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: {
      title: document.title,
      declared_language: document.declared_language,
      classification_label: document.classification_label,
      tags: document.tags.join(", "),
      metadataEntries: metadataToEntries(document.metadata),
    },
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "metadataEntries",
  });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      const metadata: Record<string, string> = {};
      for (const entry of values.metadataEntries) {
        const key = entry.key.trim();
        if (!key) continue;
        metadata[key] = entry.value;
      }
      const tags = values.tags
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean);
      return updateDocument(knowledgeBaseId, document.id, {
        title: values.title,
        declared_language: values.declared_language,
        classification_label: values.classification_label,
        tags,
        metadata,
        expected_version: document.version,
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: knowledgeKeys.document(knowledgeBaseId, document.id),
      });
      await queryClient.invalidateQueries({
        queryKey: [...knowledgeKeys.all, "contents", knowledgeBaseId],
      });
      onOpenChange(false);
    },
    onError: (error) => {
      form.setError("root", {
        message: isApiError(error) ? error.message : "Failed to save metadata",
      });
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit metadata</DialogTitle>
          <DialogDescription>
            Update title, language, classification, tags, and custom fields.
          </DialogDescription>
        </DialogHeader>
        <form
          className="space-y-4"
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <fieldset disabled={readOnly || mutation.isPending} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="meta-title">Title</Label>
              <Input id="meta-title" {...form.register("title")} />
              {form.formState.errors.title ? (
                <p className="text-xs text-destructive">{form.formState.errors.title.message}</p>
              ) : null}
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Language</Label>
                <Select
                  value={form.watch("declared_language")}
                  onValueChange={(value) =>
                    form.setValue("declared_language", value, {
                      shouldDirty: true,
                    })
                  }
                >
                  <SelectTrigger aria-label="Language">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">en</SelectItem>
                    <SelectItem value="fa">fa</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Classification</Label>
                <Select
                  value={form.watch("classification_label")}
                  onValueChange={(value) =>
                    form.setValue("classification_label", value, {
                      shouldDirty: true,
                    })
                  }
                >
                  <SelectTrigger aria-label="Classification">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="public_internal">public_internal</SelectItem>
                    <SelectItem value="restricted">restricted</SelectItem>
                    <SelectItem value="confidential">confidential</SelectItem>
                    <SelectItem value="regulated">regulated</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="meta-tags">Tags</Label>
              <Input id="meta-tags" placeholder="leave, hr, policy" {...form.register("tags")} />
              <p className="text-xs text-muted-foreground">Comma-separated labels</p>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <Label>Custom metadata</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => append({ key: "", value: "" })}
                >
                  Add field
                </Button>
              </div>
              {fields.length === 0 ? (
                <p className="text-sm text-muted-foreground">No custom fields</p>
              ) : (
                <ul className="space-y-2">
                  {fields.map((field, index) => (
                    <li key={field.id} className="grid grid-cols-[1fr_1fr_auto] gap-2">
                      <Input
                        placeholder="key"
                        aria-label={`Metadata key ${index + 1}`}
                        {...form.register(`metadataEntries.${index}.key`)}
                      />
                      <Input
                        placeholder="value"
                        aria-label={`Metadata value ${index + 1}`}
                        {...form.register(`metadataEntries.${index}.value`)}
                      />
                      <Button type="button" variant="ghost" size="sm" onClick={() => remove(index)}>
                        Remove
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </fieldset>
          {form.formState.errors.root ? (
            <p className="text-sm text-destructive" role="alert">
              {form.formState.errors.root.message}
            </p>
          ) : null}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={readOnly || mutation.isPending || !form.formState.isDirty}
            >
              {mutation.isPending ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
