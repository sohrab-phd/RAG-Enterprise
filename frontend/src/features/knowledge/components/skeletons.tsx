import * as React from "react";

import { Skeleton } from "@/components/ui/skeleton";

export function TableSkeleton({ rows = 5 }: { readonly rows?: number }): React.JSX.Element {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-10 w-full" />
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={`row-${index}`} className="h-12 w-full" />
      ))}
    </div>
  );
}

export function TreeSkeleton(): React.JSX.Element {
  return (
    <div className="space-y-2 p-2" aria-busy="true" aria-label="Loading tree">
      <Skeleton className="h-8 w-3/4" />
      <Skeleton className="ml-4 h-8 w-2/3" />
      <Skeleton className="ml-4 h-8 w-1/2" />
      <Skeleton className="h-8 w-3/5" />
    </div>
  );
}

export function InspectorSkeleton(): React.JSX.Element {
  return (
    <div className="space-y-3 p-4" aria-busy="true" aria-label="Loading detail">
      <Skeleton className="h-6 w-2/3" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
      <Skeleton className="h-24 w-full" />
    </div>
  );
}
