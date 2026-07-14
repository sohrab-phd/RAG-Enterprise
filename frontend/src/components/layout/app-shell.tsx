import * as React from "react";
import { Outlet } from "react-router-dom";

import { AppHeader } from "@/components/layout/app-header";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { LoadingLayout } from "@/components/layout/loading-layout";
import { SidebarProvider } from "@/components/layout/sidebar-context";
import { TooltipProvider } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export function AppShell(): React.JSX.Element {
  return (
    <SidebarProvider>
      <TooltipProvider>
        <div className="flex min-h-screen bg-background text-foreground">
          <a
            href="#main-content"
            className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:rounded-md focus:bg-card focus:px-3 focus:py-2 focus:text-sm focus:shadow"
          >
            Skip to main content
          </a>
          <AppSidebar />
          <div className={cn("flex min-h-screen min-w-0 flex-1 flex-col")}>
            <AppHeader />
            <main
              id="main-content"
              className="mx-auto w-full max-w-[1600px] flex-1 px-3 py-5 sm:px-4 lg:px-6"
            >
              <React.Suspense fallback={<LoadingLayout />}>
                <Outlet />
              </React.Suspense>
            </main>
          </div>
        </div>
      </TooltipProvider>
    </SidebarProvider>
  );
}
