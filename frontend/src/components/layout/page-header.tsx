import * as React from "react";

import { cn } from "@/lib/utils";

type PageHeaderProps = {
  readonly title: string;
  readonly description?: string;
  readonly actions?: React.ReactNode;
  readonly className?: string;
};

export function PageHeader({
  title,
  description,
  actions,
  className,
}: PageHeaderProps): React.JSX.Element {
  return (
    <div
      className={cn(
        "mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between",
        className,
      )}
    >
      <div className="min-w-0 space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
        {description ? (
          <p className="max-w-2xl text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}
