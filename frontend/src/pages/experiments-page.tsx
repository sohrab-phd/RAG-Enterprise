import * as React from "react";
import { useLocation } from "react-router-dom";

import { ModulePlaceholder } from "@/pages/module-placeholder";

export function ExperimentsPage(): React.JSX.Element {
  const { pathname } = useLocation();
  return (
    <ModulePlaceholder
      title="Experiments"
      description="Configure offline experiments, inspect results, and compare runs."
      routeHint={pathname}
    />
  );
}
