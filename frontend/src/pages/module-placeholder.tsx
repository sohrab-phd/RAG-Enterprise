import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";

type ModulePlaceholderProps = {
  readonly title: string;
  readonly description: string;
  readonly routeHint?: string;
};

export function ModulePlaceholder({
  title,
  description,
  routeHint,
}: ModulePlaceholderProps): React.JSX.Element {
  return (
    <section aria-labelledby="module-heading">
      <PageHeader title={title} description={description} />
      <div className="rounded-lg border border-dashed border-border bg-card/60 p-8">
        <p id="module-heading" className="sr-only">
          {title}
        </p>
        <p className="text-sm text-muted-foreground">
          This module shell is ready. Business features are not implemented yet.
        </p>
        {routeHint ? (
          <p className="mt-3 font-mono text-xs text-muted-foreground">Route: {routeHint}</p>
        ) : null}
      </div>
    </section>
  );
}
