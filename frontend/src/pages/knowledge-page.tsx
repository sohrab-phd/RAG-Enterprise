import * as React from "react";
import { useLocation } from "react-router-dom";

import { ModulePlaceholder } from "@/pages/module-placeholder";

export function KnowledgePage(): React.JSX.Element {
  const { pathname } = useLocation();
  return (
    <ModulePlaceholder
      title="Knowledge"
      description="Manage knowledge bases, folder trees, uploads, metadata, and processing status."
      routeHint={pathname}
    />
  );
}
