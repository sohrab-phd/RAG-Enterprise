import * as React from "react";
import { isRouteErrorResponse, Link, useRouteError } from "react-router-dom";

import { Button } from "@/components/ui/button";

export function RouteErrorPage(): React.JSX.Element {
  const error = useRouteError();

  let title = "Unexpected application error";
  let detail = "An error occurred while rendering this route.";

  if (isRouteErrorResponse(error)) {
    title = `${error.status} ${error.statusText}`;
    detail =
      typeof error.data === "string" ? error.data : "The requested route could not be handled.";
  } else if (error instanceof Error) {
    detail = error.message;
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <div
        role="alert"
        className="w-full max-w-lg space-y-4 rounded-lg border border-border bg-card p-6 shadow-sm"
      >
        <div className="space-y-1">
          <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
          <p className="text-sm text-muted-foreground">{detail}</p>
        </div>
        <Button type="button" asChild>
          <Link to="/knowledge">Back to Knowledge</Link>
        </Button>
      </div>
    </div>
  );
}
