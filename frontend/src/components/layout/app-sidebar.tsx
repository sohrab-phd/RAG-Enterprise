import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import * as React from "react";

import { PrimaryNav, SidebarBrand } from "@/components/layout/primary-nav";
import { useSidebar } from "@/components/layout/sidebar-context";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

export function AppSidebar(): React.JSX.Element {
  const { collapsed, mobileOpen, setMobileOpen, toggleCollapsed } = useSidebar();

  return (
    <>
      {mobileOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-foreground/40 lg:hidden"
          aria-label="Close navigation overlay"
          onClick={() => setMobileOpen(false)}
        />
      ) : null}

      <aside
        id="app-sidebar"
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width,transform] duration-200",
          "lg:static lg:translate-x-0",
          collapsed ? "w-[72px]" : "w-60",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
        )}
        aria-label="Application sidebar"
      >
        <SidebarBrand collapsed={collapsed} />
        <PrimaryNav collapsed={collapsed} onNavigate={() => setMobileOpen(false)} />
        <div className="mt-auto space-y-2 p-2">
          <Separator />
          <Button
            type="button"
            variant="ghost"
            size={collapsed ? "icon" : "sm"}
            className={cn(
              "w-full text-sidebar-foreground",
              collapsed ? "justify-center" : "justify-start",
            )}
            onClick={toggleCollapsed}
            aria-pressed={collapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <PanelLeftOpen className="size-4" aria-hidden />
            ) : (
              <>
                <PanelLeftClose className="size-4" aria-hidden />
                <span>Collapse</span>
              </>
            )}
          </Button>
        </div>
      </aside>
    </>
  );
}
