import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { listKnowledgeBases, publishKnowledgeBase } from "@/features/knowledge/api";
import { CreateKnowledgeBaseDialog } from "@/features/knowledge/components/create-kb-dialog";
import { EmptyState } from "@/features/knowledge/components/empty-state";
import { ErrorState } from "@/features/knowledge/components/error-state";
import { TableSkeleton } from "@/features/knowledge/components/skeletons";
import { StatusChip } from "@/features/knowledge/components/status-chip";
import { formatRelativeTime } from "@/features/knowledge/lib/format";
import { knowledgeKeys } from "@/features/knowledge/query-keys";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { isApiError } from "@/lib/api/types";

export function KnowledgeBaseList(): React.JSX.Element {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [createOpen, setCreateOpen] = React.useState(false);
  const [publishError, setPublishError] = React.useState<string | null>(null);
  const [publishingId, setPublishingId] = React.useState<string | null>(null);
  const page = Number(searchParams.get("page") ?? "1") || 1;
  const status = searchParams.get("status") ?? "all";
  const qParam = searchParams.get("q") ?? "";
  const [qInput, setQInput] = React.useState(qParam);
  const debouncedQ = useDebouncedValue(qInput, 300);

  const publishMutation = useMutation({
    mutationFn: publishKnowledgeBase,
    onMutate: (knowledgeBaseId) => {
      setPublishingId(knowledgeBaseId);
      setPublishError(null);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: knowledgeKeys.bases() });
    },
    onError: (error) => {
      setPublishError(isApiError(error) ? error.message : "Publish failed");
    },
    onSettled: () => {
      setPublishingId(null);
    },
  });

  React.useEffect(() => {
    const next = new URLSearchParams(searchParams);
    if (debouncedQ.trim()) next.set("q", debouncedQ.trim());
    else next.delete("q");
    if ((next.get("q") ?? "") === qParam) {
      return;
    }
    next.set("page", "1");
    setSearchParams(next, { replace: true });
  }, [debouncedQ, qParam, searchParams, setSearchParams]);

  const filters = {
    page,
    pageSize: 20,
    status: status === "all" ? undefined : status,
    q: qParam.trim() || undefined,
  };

  const query = useQuery({
    queryKey: knowledgeKeys.baseList(filters),
    queryFn: ({ signal }) => listKnowledgeBases({ ...filters, signal }),
  });

  const items = query.data?.items ?? [];
  const pagination = query.data?.pagination;
  const isInitialLoading = query.isLoading && !query.data;

  return (
    <section aria-labelledby="kb-list-heading">
      <PageHeader
        title="Knowledge bases"
        description="Browse and create curated corpora for documents and retrieval."
        actions={
          <Button type="button" onClick={() => setCreateOpen(true)} disabled={isInitialLoading}>
            Create knowledge base
          </Button>
        }
      />
      <h2 id="kb-list-heading" className="sr-only">
        Knowledge base list
      </h2>

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
        <Input
          value={qInput}
          onChange={(event) => setQInput(event.target.value)}
          placeholder="Search by name"
          aria-label="Search knowledge bases"
          className="sm:max-w-xs"
        />
        <Select
          value={status}
          onValueChange={(value) => {
            const next = new URLSearchParams(searchParams);
            if (value === "all") next.delete("status");
            else next.set("status", value);
            next.set("page", "1");
            setSearchParams(next);
          }}
        >
          <SelectTrigger className="sm:w-44" aria-label="Filter by status">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="draft">draft</SelectItem>
            <SelectItem value="active">active</SelectItem>
            <SelectItem value="reindexing">reindexing</SelectItem>
            <SelectItem value="archived">archived</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isInitialLoading ? <TableSkeleton /> : null}
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : null}
      {publishError ? (
        <p className="mb-3 text-sm text-destructive" role="alert">
          {publishError}
        </p>
      ) : null}

      {!isInitialLoading && !query.isError && items.length === 0 ? (
        <EmptyState
          title="No knowledge bases yet"
          description="Create a knowledge base to start organizing documents."
          actionLabel="Create knowledge base"
          onAction={() => setCreateOpen(true)}
        />
      ) : null}

      {!isInitialLoading && !query.isError && items.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-border bg-card">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-border bg-muted/40">
              <tr>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Docs</th>
                <th className="px-4 py-3 font-medium">Language</th>
                <th className="px-4 py-3 font-medium">Updated</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((kb) => (
                <tr key={kb.id} className="border-b border-border last:border-0 hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <Link
                      to={`/knowledge/${kb.id}`}
                      className="font-medium text-foreground hover:underline"
                    >
                      {kb.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <StatusChip status={kb.status} />
                  </td>
                  <td className="px-4 py-3 tabular-nums text-muted-foreground">
                    {kb.document_count}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{kb.default_language}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {formatRelativeTime(kb.updated_at)}
                  </td>
                  <td className="px-4 py-3">
                    {kb.status === "draft" ? (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={publishingId === kb.id}
                        onClick={() => publishMutation.mutate(kb.id)}
                      >
                        {publishingId === kb.id ? "Publishing…" : "Publish"}
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {pagination && pagination.total_pages > 1 ? (
        <div className="mt-4 flex items-center justify-between gap-2">
          <p className="text-xs text-muted-foreground">
            Page {pagination.page} of {pagination.total_pages} · {pagination.total_items} total
          </p>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!pagination.has_previous}
              onClick={() => {
                const next = new URLSearchParams(searchParams);
                next.set("page", String(page - 1));
                setSearchParams(next);
              }}
            >
              Previous
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!pagination.has_next}
              onClick={() => {
                const next = new URLSearchParams(searchParams);
                next.set("page", String(page + 1));
                setSearchParams(next);
              }}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}

      <CreateKnowledgeBaseDialog open={createOpen} onOpenChange={setCreateOpen} />
    </section>
  );
}
