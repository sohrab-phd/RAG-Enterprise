import * as React from "react";
import { useLocation } from "react-router-dom";

import { ModulePlaceholder } from "@/pages/module-placeholder";

export function EvaluationPage(): React.JSX.Element {
  const { pathname } = useLocation();
  return (
    <ModulePlaceholder
      title="Evaluation"
      description="Review offline RAG quality metrics and recent evaluation runs."
      routeHint={pathname}
    />
  );
}
