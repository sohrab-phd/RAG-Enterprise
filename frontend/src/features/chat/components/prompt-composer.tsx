import { zodResolver } from "@hookform/resolvers/zod";
import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { KnowledgeBaseSummary } from "@/features/knowledge/types";

const schema = z.object({
  question: z.string().trim().min(1, "Enter a question"),
});

type FormValues = z.infer<typeof schema>;

type PromptComposerProps = {
  readonly knowledgeBases: readonly KnowledgeBaseSummary[];
  readonly knowledgeBasesLoading: boolean;
  readonly knowledgeBaseId: string | null;
  readonly onKnowledgeBaseChange: (id: string) => void;
  readonly topK: number;
  readonly onTopKChange: (value: number) => void;
  readonly disabled?: boolean;
  readonly submitting?: boolean;
  readonly onSubmit: (question: string) => void;
};

export function PromptComposer({
  knowledgeBases,
  knowledgeBasesLoading,
  knowledgeBaseId,
  onKnowledgeBaseChange,
  topK,
  onTopKChange,
  disabled = false,
  submitting = false,
  onSubmit,
}: PromptComposerProps): React.JSX.Element {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { question: "" },
  });

  const kbReady = Boolean(knowledgeBaseId);
  const blocked = disabled || submitting || !kbReady;

  return (
    <form
      className="space-y-3 border-t border-border bg-card p-3"
      onSubmit={handleSubmit((values) => {
        onSubmit(values.question.trim());
        reset({ question: "" });
      })}
      noValidate
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="min-w-0 flex-1 space-y-1.5">
          <Label htmlFor="chat-kb">Knowledge base</Label>
          <Select
            value={knowledgeBaseId ?? ""}
            onValueChange={onKnowledgeBaseChange}
            disabled={knowledgeBasesLoading || submitting}
          >
            <SelectTrigger id="chat-kb" aria-label="Knowledge base">
              <SelectValue
                placeholder={knowledgeBasesLoading ? "Loading…" : "Select a knowledge base"}
              />
            </SelectTrigger>
            <SelectContent>
              {knowledgeBases.length === 0 ? (
                <SelectItem value="__empty__" disabled>
                  No knowledge bases
                </SelectItem>
              ) : null}
              {knowledgeBases.map((kb) => (
                <SelectItem key={kb.id} value={kb.id}>
                  {kb.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="w-full space-y-1.5 sm:w-28">
          <Label htmlFor="chat-topk">top_k</Label>
          <Select
            value={String(topK)}
            onValueChange={(value) => onTopKChange(Number(value))}
            disabled={submitting}
          >
            <SelectTrigger id="chat-topk" aria-label="top_k">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[4, 6, 8, 10, 12, 16].map((value) => (
                <SelectItem key={value} value={String(value)}>
                  {value}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="chat-question">Question</Label>
        <Textarea
          id="chat-question"
          rows={3}
          placeholder={
            kbReady
              ? "Ask about this knowledge base…"
              : "Select a knowledge base to enable the composer"
          }
          disabled={blocked}
          {...register("question")}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              if (!blocked) {
                void handleSubmit((values) => {
                  onSubmit(values.question.trim());
                  reset({ question: "" });
                })();
              }
            }
          }}
        />
        {errors.question ? (
          <p className="text-xs text-destructive">{errors.question.message}</p>
        ) : null}
        {!kbReady ? (
          <p className="text-xs text-muted-foreground">Select a knowledge base before sending.</p>
        ) : null}
      </div>

      <div className="flex justify-end">
        <Button type="submit" disabled={blocked}>
          {submitting ? "Sending…" : "Send"}
        </Button>
      </div>
    </form>
  );
}
