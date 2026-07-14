import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { getDocument } from "@/features/knowledge/api";
import { EmptyState } from "@/features/knowledge/components/empty-state";
import { ErrorState } from "@/features/knowledge/components/error-state";
import { MetadataDrawer } from "@/features/knowledge/components/metadata-drawer";
import { ProcessingStatusPanel } from "@/features/knowledge/components/processing-status-panel";
import { InspectorSkeleton } from "@/features/knowledge/components/skeletons";
import { StatusChip } from "@/features/knowledge/components/status-chip";
import { formatRelativeTime } from "@/features/knowledge/lib/format";
import { knowledgeKeys } from "@/features/knowledge/query-keys";
import type { DocumentVersionSummary } from "@/features/knowledge/types";

type DocumentInspectorProps = {
  readonly knowledgeBaseId: string;
  readonly documentId: string | null;
};

export function DocumentInspector({
  knowledgeBaseId,
  documentId,
}: DocumentInspectorProps): React.JSX.Element {
  const queryClient = useQueryClient();
  const [metadataOpen, setMetadataOpen] = React.useState(false);

  const documentQuery = useQuery({
    queryKey: knowledgeKeys.document(knowledgeBaseId, documentId ?? ""),
    queryFn: ({ signal }) => getDocument(knowledgeBaseId, documentId as string, signal),
    enabled: Boolean(documentId),
  });

  const versionQuery = useQuery({
    queryKey: knowledgeKeys.lastVersion(knowledgeBaseId, documentId ?? ""),
    queryFn: async (): Promise<DocumentVersionSummary | null> => {
      return (
        queryClient.getQueryData<DocumentVersionSummary>(
          knowledgeKeys.lastVersion(knowledgeBaseId, documentId as string),
        ) ?? null
      );
    },
    enabled: Boolean(documentId),
    staleTime: Infinity,
  });

  if (!documentId) {
    return (
      <div className="p-4">
        <EmptyState
          title="Select a document"
          description="Choose a document from the list to inspect metadata and processing status."
        />
      </div>
    );
  }

  if (documentQuery.isLoading) {
    return <InspectorSkeleton />;
  }

  if (documentQuery.isError) {
    return (
      <div className="p-4">
        <ErrorState error={documentQuery.error} onRetry={() => void documentQuery.refetch()} />
      </div>
    );
  }

  const document = documentQuery.data;
  if (!document) {
    return (
      <div className="p-4">
        <EmptyState title="Document not found" />
      </div>
    );
  }

  return (
    <div className="space-y-5 p-4">
      <div className="space-y-2">
        <h2 className="text-lg font-semibold tracking-tight">{document.title}</h2>
        <div className="flex flex-wrap gap-2">
          <StatusChip status={document.status} />
          <span className="text-xs text-muted-foreground">
            Updated {formatRelativeTime(document.updated_at)}
          </span>
        </div>
      </div>

      <dl className="grid gap-2 text-sm">
        <div className="flex justify-between gap-3">
          <dt className="text-muted-foreground">Language</dt>
          <dd>{document.declared_language}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted-foreground">Classification</dt>
          <dd>{document.classification_label}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted-foreground">Tags</dt>
          <dd className="text-right">
            {document.tags.length > 0 ? document.tags.join(", ") : "—"}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted-foreground">Current version</dt>
          <dd className="max-w-[10rem] truncate font-mono text-xs">
            {document.current_version_id ?? "—"}
          </dd>
        </div>
      </dl>

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setMetadataOpen(true)}
          disabled={document.status === "archived" || document.status === "deleted"}
        >
          Edit metadata
        </Button>
      </div>

      <section aria-labelledby="processing-heading" className="space-y-2">
        <h3 id="processing-heading" className="text-sm font-medium">
          Processing status
        </h3>
        <ProcessingStatusPanel
          knowledgeBaseId={knowledgeBaseId}
          documentId={document.id}
          version={versionQuery.data ?? null}
          hasCurrentVersion={Boolean(document.current_version_id)}
        />
      </section>

      <MetadataDrawer
        open={metadataOpen}
        onOpenChange={setMetadataOpen}
        knowledgeBaseId={knowledgeBaseId}
        document={document}
      />
    </div>
  );
}
