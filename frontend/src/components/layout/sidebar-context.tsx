import * as React from "react";

type SidebarContextValue = {
  readonly collapsed: boolean;
  readonly mobileOpen: boolean;
  readonly setCollapsed: (collapsed: boolean) => void;
  readonly toggleCollapsed: () => void;
  readonly setMobileOpen: (open: boolean) => void;
  readonly toggleMobileOpen: () => void;
};

const SidebarContext = React.createContext<SidebarContextValue | null>(null);

const STORAGE_KEY = "rag-enterprise-sidebar-collapsed";

export function SidebarProvider({
  children,
}: {
  readonly children: React.ReactNode;
}): React.JSX.Element {
  const [collapsed, setCollapsedState] = React.useState(() => {
    if (typeof window === "undefined") {
      return false;
    }
    return window.localStorage.getItem(STORAGE_KEY) === "true";
  });
  const [mobileOpen, setMobileOpen] = React.useState(false);

  const setCollapsed = React.useCallback((next: boolean) => {
    setCollapsedState(next);
    window.localStorage.setItem(STORAGE_KEY, String(next));
  }, []);

  const toggleCollapsed = React.useCallback(() => {
    setCollapsed(!collapsed);
  }, [collapsed, setCollapsed]);

  const toggleMobileOpen = React.useCallback(() => {
    setMobileOpen((open) => !open);
  }, []);

  React.useEffect(() => {
    const onResize = (): void => {
      if (window.innerWidth >= 1024) {
        setMobileOpen(false);
      }
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const value = React.useMemo(
    () => ({
      collapsed,
      mobileOpen,
      setCollapsed,
      toggleCollapsed,
      setMobileOpen,
      toggleMobileOpen,
    }),
    [collapsed, mobileOpen, setCollapsed, toggleCollapsed, toggleMobileOpen],
  );

  return <SidebarContext.Provider value={value}>{children}</SidebarContext.Provider>;
}

export function useSidebar(): SidebarContextValue {
  const context = React.useContext(SidebarContext);
  if (context === null) {
    throw new Error("useSidebar must be used within SidebarProvider");
  }
  return context;
}
