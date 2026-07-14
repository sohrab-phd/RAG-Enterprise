import * as React from "react";

import { Skeleton } from "@/components/ui/skeleton";

export function LoadingLayout({
  label = "Loading module",
}: {
  readonly label?: string;
}): React.JSX.Element {
  return (
    <div className="space-y-6" role="status" aria-live="polite" aria-label={label}>
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-28 w-full md:col-span-2 xl:col-span-1" />
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
