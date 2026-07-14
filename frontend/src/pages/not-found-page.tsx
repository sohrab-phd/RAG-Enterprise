import * as React from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

export function NotFoundPage(): React.JSX.Element {
  return (
    <section
      className="flex min-h-[60vh] flex-col items-start justify-center gap-4"
      aria-labelledby="not-found-heading"
    >
      <p className="text-sm font-medium text-muted-foreground">404</p>
      <h1 id="not-found-heading" className="text-2xl font-semibold tracking-tight">
        Page not found
      </h1>
      <p className="max-w-md text-sm text-muted-foreground">
        The route you requested is not part of the application shell. Return to Knowledge or pick a
        module from the sidebar.
      </p>
      <Button type="button" asChild>
        <Link to="/knowledge">Back to Knowledge</Link>
      </Button>
    </section>
  );
}
