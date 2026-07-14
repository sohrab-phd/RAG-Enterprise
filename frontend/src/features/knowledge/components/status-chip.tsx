import * as React from "react";

import { Badge, type BadgeProps } from "@/components/ui/badge";

type StatusChipProps = {
  readonly status: string;
  readonly className?: string;
};

function toneForStatus(status: string): BadgeProps["variant"] {
  switch (status) {
    case "active":
    case "indexed":
    case "completed":
    case "passed":
    case "extracted":
    case "chunked":
      return "success";
    case "draft":
    case "uploaded":
    case "pending":
      return "secondary";
    case "processing":
    case "extracting":
    case "chunking":
    case "indexing":
    case "reindexing":
    case "uploading":
      return "info";
    case "failed":
    case "deleted":
      return "danger";
    case "abstained":
    case "archived":
    case "superseded":
    case "expired":
    case "cancelled":
      return "warning";
    default:
      return "outline";
  }
}

export function StatusChip({ status, className }: StatusChipProps): React.JSX.Element {
  return (
    <Badge variant={toneForStatus(status)} className={className}>
      <span className="sr-only">Status: </span>
      {status}
    </Badge>
  );
}
