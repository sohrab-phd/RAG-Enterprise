import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ThemeProvider } from "@/components/theme/theme-provider";
import { appRoutes } from "@/routes";

function renderApp(initialEntry = "/knowledge"): ReturnType<typeof render> {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const router = createMemoryRouter(appRoutes, {
    initialEntries: [initialEntry],
  });

  return render(
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ThemeProvider>,
  );
}

describe("application shell", () => {
  it("renders sidebar navigation and knowledge placeholder", () => {
    renderApp("/knowledge");

    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Knowledge" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Chat" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Evaluation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Experiments" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Knowledge" })).toBeInTheDocument();
    expect(screen.getByText(/Development actor stub/i)).toBeInTheDocument();
  });

  it("navigates between module placeholders", async () => {
    const user = userEvent.setup();
    renderApp("/knowledge");

    await user.click(screen.getByRole("link", { name: "Chat" }));
    expect(screen.getByRole("heading", { name: "Chat" })).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Evaluation" }));
    expect(screen.getByRole("heading", { name: "Evaluation" })).toBeInTheDocument();
  });

  it("renders the 404 page for unknown routes", () => {
    renderApp("/does-not-exist");

    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to Knowledge" })).toBeInTheDocument();
  });

  it("renders settings hub links", () => {
    renderApp("/settings");

    expect(screen.getByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Providers" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "System" })).toBeInTheDocument();
  });
});
