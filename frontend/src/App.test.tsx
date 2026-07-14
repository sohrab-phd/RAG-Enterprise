import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ThemeProvider } from "@/components/theme/theme-provider";
import { appRoutes } from "@/routes";

function renderApp(initialEntry = "/knowledge"): ReturnType<typeof render> {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
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

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("application shell", () => {
  it("renders sidebar navigation", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({
          success: true,
          data: {
            items: [],
            pagination: {
              page: 1,
              page_size: 20,
              total_items: 0,
              total_pages: 0,
              has_next: false,
              has_previous: false,
            },
          },
        }),
      ),
    );

    renderApp("/knowledge");

    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Knowledge" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Chat" })).toBeInTheDocument();
  });

  it("renders the 404 page for unknown routes", () => {
    renderApp("/does-not-exist");

    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });
});

describe("knowledge module", () => {
  it("lists knowledge bases from the API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/knowledge-bases?") || url.endsWith("/knowledge-bases")) {
          return Response.json({
            success: true,
            data: {
              items: [
                {
                  id: "018f0000-0000-7000-8000-0000000000b1",
                  name: "Policies KB",
                  status: "active",
                  default_language: "fa",
                  visibility_policy: "workspace",
                  document_count: 42,
                  created_at: "2026-07-14T00:00:00Z",
                  updated_at: "2026-07-14T12:00:00Z",
                },
              ],
              pagination: {
                page: 1,
                page_size: 20,
                total_items: 1,
                total_pages: 1,
                has_next: false,
                has_previous: false,
              },
            },
          });
        }
        return Response.json(
          { success: false, error: { code: "not_found", message: "missing" } },
          { status: 404 },
        );
      }),
    );

    renderApp("/knowledge");

    expect(await screen.findByRole("heading", { name: "Knowledge bases" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Policies KB" })).toBeInTheDocument();
    expect(screen.getByText("active")).toBeInTheDocument();
  });

  it("shows empty state when no knowledge bases exist", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({
          success: true,
          data: {
            items: [],
            pagination: {
              page: 1,
              page_size: 20,
              total_items: 0,
              total_pages: 0,
              has_next: false,
              has_previous: false,
            },
          },
        }),
      ),
    );

    renderApp("/knowledge");

    expect(await screen.findByText("No knowledge bases yet")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Create knowledge base" }).length).toBeGreaterThan(
      0,
    );
  });

  it("shows error state when the list API fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json(
          {
            success: false,
            error: { code: "forbidden", message: "Permission denied" },
          },
          { status: 403 },
        ),
      ),
    );

    renderApp("/knowledge");

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/forbidden/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("opens create dialog and submits a new knowledge base", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (method === "GET") {
        return Response.json({
          success: true,
          data: {
            items: [],
            pagination: {
              page: 1,
              page_size: 20,
              total_items: 0,
              total_pages: 0,
              has_next: false,
              has_previous: false,
            },
          },
        });
      }
      if (method === "POST" && url.includes("/knowledge-bases")) {
        return Response.json(
          {
            success: true,
            data: {
              id: "018f0000-0000-7000-8000-0000000000b2",
              name: "Engineering Docs",
              status: "draft",
              default_language: "en",
              visibility_policy: "workspace",
              document_count: 0,
              created_at: "2026-07-14T00:00:00Z",
              updated_at: "2026-07-14T00:00:00Z",
              description: null,
              version: 1,
            },
          },
          { status: 201 },
        );
      }
      return Response.json(
        { success: false, error: { code: "not_found", message: "missing" } },
        { status: 404 },
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    renderApp("/knowledge");
    await screen.findByText("No knowledge bases yet");

    await user.click(screen.getAllByRole("button", { name: "Create knowledge base" })[0]!);
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText("Name"), "Engineering Docs");
    await user.click(within(dialog).getByRole("button", { name: "Create" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/knowledge-bases"),
        expect.objectContaining({ method: "POST" }),
      );
    });
  });
});
