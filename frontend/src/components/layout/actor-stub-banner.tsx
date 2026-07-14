import * as React from "react";
import { Link } from "react-router-dom";

import { cn } from "@/lib/utils";

type ActorStubBannerProps = {
  readonly className?: string;
};

export function ActorStubBanner({ className }: ActorStubBannerProps): React.JSX.Element {
  return (
    <div
      role="status"
      className={cn(
        "border-b border-warning/30 bg-warning/10 px-4 py-2 text-xs text-foreground",
        className,
      )}
    >
      <p>
        Development actor stub: requests use{" "}
        <code className="font-mono text-[0.7rem]">X-User-Id</code> and{" "}
        <code className="font-mono text-[0.7rem]">X-Organization-Id</code> headers. Authentication
        UI is out of scope.{" "}
        <Link to="/settings/system" className="font-medium underline-offset-2 hover:underline">
          System settings
        </Link>
      </p>
    </div>
  );
}
