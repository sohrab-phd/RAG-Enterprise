import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as React from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { ErrorBoundary } from "@/components/error-boundary";
import { ThemeProvider } from "@/components/theme/theme-provider";
import { appRoutes } from "@/routes";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const router = createBrowserRouter(appRoutes);

export default function App(): React.JSX.Element {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
