import * as React from "react";

import { Button } from "@/components/ui/button";
import { isApiError } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type ErrorStateProps = {
  readonly error: unknown;
  readonly onRetry?: () => void;
  readonly className?: string;
  readonly title?: string;
};

export function ErrorState({
  error,
  onRetry,
  className,
  title = "Something went wrong",
}: ErrorStateProps): React.JSX.Element {
  const message = isApiError(error)
    ? `${error.code}: ${error.message}`
    : error instanceof Error
      ? error.message
      : "Unexpected error";

  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4",
        className,
      )}
    >
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">{title}</p>
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>
      {onRetry ? (
        <Button type="button" variant="outline" size="sm" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </div>
  );
}
