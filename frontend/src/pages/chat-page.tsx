import * as React from "react";
import { useLocation } from "react-router-dom";

import { ModulePlaceholder } from "@/pages/module-placeholder";

export function ChatPage(): React.JSX.Element {
  const { pathname } = useLocation();
  return (
    <ModulePlaceholder
      title="Chat"
      description="Grounded Q&A with conversation history, citations, and an evidence panel."
      routeHint={pathname}
    />
  );
}
