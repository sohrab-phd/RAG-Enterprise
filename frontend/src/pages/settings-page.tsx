import * as React from "react";
import { Link, useLocation } from "react-router-dom";

import { PageHeader } from "@/components/layout/page-header";
import { ModulePlaceholder } from "@/pages/module-placeholder";

const SETTINGS_LINKS = [
  { to: "/settings/providers", label: "Providers" },
  { to: "/settings/models", label: "Models" },
  { to: "/settings/prompts", label: "Prompt templates" },
  { to: "/settings/system", label: "System" },
] as const;

export function SettingsPage(): React.JSX.Element {
  const { pathname } = useLocation();
  const isHub = pathname === "/settings";

  if (!isHub) {
    const section =
      SETTINGS_LINKS.find((item) => pathname.startsWith(item.to))?.label ?? "Settings";
    return (
      <ModulePlaceholder
        title={section}
        description="Settings section placeholder. Configuration APIs are not wired yet."
        routeHint={pathname}
      />
    );
  }

  return (
    <section aria-labelledby="settings-heading">
      <PageHeader
        title="Settings"
        description="Inspect providers, models, prompt templates, and system context."
      />
      <h2 id="settings-heading" className="sr-only">
        Settings sections
      </h2>
      <ul className="grid gap-3 sm:grid-cols-2">
        {SETTINGS_LINKS.map((item) => (
          <li key={item.to}>
            <Link
              to={item.to}
              className="block rounded-lg border border-border bg-card p-4 text-sm font-medium transition-colors hover:bg-muted"
            >
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
