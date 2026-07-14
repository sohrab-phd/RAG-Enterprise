import * as React from "react";
import { Link, NavLink } from "react-router-dom";

import { useSidebar } from "@/components/layout/sidebar-context";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { PRIMARY_NAV } from "@/lib/navigation";
import { cn } from "@/lib/utils";

type PrimaryNavProps = {
  readonly collapsed: boolean;
  readonly onNavigate?: () => void;
};

export function PrimaryNav({ collapsed, onNavigate }: PrimaryNavProps): React.JSX.Element {
  return (
    <nav aria-label="Primary" className="flex flex-1 flex-col gap-1 px-2 py-3">
      {PRIMARY_NAV.map((item) => {
        const Icon = item.icon;
        const linkClassName = ({ isActive }: { isActive: boolean }): string =>
          cn(
            "group flex items-center gap-3 rounded-md px-2.5 py-2 text-sm font-medium text-sidebar-foreground transition-colors",
            "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
            isActive && "bg-sidebar-accent text-sidebar-accent-foreground shadow-sm",
            collapsed && "justify-center px-0",
          );

        const link = (
          <NavLink
            to={item.to}
            onClick={onNavigate}
            className={linkClassName}
            aria-label={item.label}
            title={collapsed ? undefined : item.description}
          >
            <Icon className="size-4 shrink-0" aria-hidden />
            {!collapsed ? <span>{item.label}</span> : null}
          </NavLink>
        );

        if (!collapsed) {
          return <React.Fragment key={item.to}>{link}</React.Fragment>;
        }

        return (
          <Tooltip key={item.to}>
            <TooltipTrigger asChild>{link}</TooltipTrigger>
            <TooltipContent side="right">{item.label}</TooltipContent>
          </Tooltip>
        );
      })}
    </nav>
  );
}

export function SidebarBrand({ collapsed }: { readonly collapsed: boolean }): React.JSX.Element {
  const { setMobileOpen } = useSidebar();

  return (
    <div
      className={cn(
        "flex h-14 items-center border-b border-sidebar-border px-3",
        collapsed && "justify-center px-0",
      )}
    >
      <Link
        to="/knowledge"
        className="flex items-center gap-2 rounded-md px-1 py-1 text-sidebar-foreground"
        onClick={() => setMobileOpen(false)}
      >
        <span
          className="flex size-8 items-center justify-center rounded-md bg-primary text-xs font-semibold text-primary-foreground"
          aria-hidden
        >
          RE
        </span>
        {!collapsed ? (
          <span className="text-sm font-semibold tracking-tight">RAG-enterprise</span>
        ) : (
          <span className="sr-only">RAG-enterprise</span>
        )}
      </Link>
    </div>
  );
}
