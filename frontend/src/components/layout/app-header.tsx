import { Menu, Moon, Sun } from "lucide-react";
import * as React from "react";
import { useLocation, useNavigation } from "react-router-dom";

import { ActorStubBanner } from "@/components/layout/actor-stub-banner";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { useSidebar } from "@/components/layout/sidebar-context";
import { WorkspaceBadge } from "@/components/layout/workspace-badge";
import { useTheme } from "@/components/theme/theme-provider";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function AppHeader(): React.JSX.Element {
  const { pathname } = useLocation();
  const navigation = useNavigation();
  const { toggleMobileOpen } = useSidebar();
  const { theme, toggleTheme } = useTheme();
  const isNavigating = navigation.state === "loading";

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <ActorStubBanner />
      <div className="flex h-14 items-center gap-3 px-3 sm:px-4">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={toggleMobileOpen}
          aria-controls="app-sidebar"
          aria-label="Open navigation"
        >
          <Menu className="size-4" aria-hidden />
        </Button>

        <div className="min-w-0 flex-1">
          <Breadcrumbs pathname={pathname} />
        </div>

        <div className="flex items-center gap-2">
          <WorkspaceBadge className="hidden sm:inline-flex" />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          >
            {theme === "dark" ? (
              <Sun className="size-4" aria-hidden />
            ) : (
              <Moon className="size-4" aria-hidden />
            )}
          </Button>
        </div>
      </div>
      <div
        className={cn(
          "h-0.5 w-full bg-primary transition-opacity",
          isNavigating ? "opacity-100" : "opacity-0",
        )}
        role="status"
        aria-live="polite"
        aria-label={isNavigating ? "Loading page" : undefined}
      />
    </header>
  );
}
