import * as React from "react";

import { getAppConfig } from "@/lib/config";
import { cn } from "@/lib/utils";

type WorkspaceBadgeProps = {
  readonly name?: string;
  readonly className?: string;
};

export function WorkspaceBadge({
  name = getAppConfig().workspaceName,
  className,
}: WorkspaceBadgeProps): React.JSX.Element {
  return (
    <div
      className={cn(
        "inline-flex max-w-[14rem] items-center gap-2 truncate rounded-md border border-border bg-card px-2.5 py-1 text-xs text-muted-foreground",
        className,
      )}
    >
      <span className="size-1.5 shrink-0 rounded-full bg-success" aria-hidden />
      <span className="truncate">
        <span className="sr-only">Current workspace: </span>
        Workspace · {name}
      </span>
    </div>
  );
}
