import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ThemeProvider } from "@/components/theme/theme-provider";
import { appRoutes } from "@/routes";

const kbId = "018f0000-0000-7000-8000-0000000000b1";
const docId = "018f0000-0000-7000-8000-0000000000d1";

function renderBrowser(): ReturnType<typeof render> {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const router = createMemoryRouter(appRoutes, {
    initialEntries: [`/knowledge/${kbId}`],
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

describe("document deletion", () => {
  it("deletes a document after confirmation and refreshes the list", async () => {
    const user = userEvent.setup();
    let deleted = false;

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = (init?.method ?? "GET").toUpperCase();

        if (method === "DELETE" && url.includes(`/documents/${docId}`)) {
          deleted = true;
          return new Response(null, { status: 204 });
        }

        if (url.includes(`/knowledge-bases/${kbId}/contents`)) {
          return Response.json({
            success: true,
            data: {
              folders: [],
              documents: deleted
                ? []
                : [
                    {
                      id: docId,
                      title: "Employee Handbook",
                      status: "active",
                      declared_language: "en",
                      classification_label: "public_internal",
                      folder_id: null,
                      current_version_id: "018f0000-0000-7000-8000-0000000000v1",
                      updated_at: "2026-07-14T12:00:00Z",
                      created_at: "2026-07-14T00:00:00Z",
                    },
                  ],
              pagination: {
                page: 1,
                page_size: 50,
                total_items: deleted ? 0 : 1,
                total_pages: deleted ? 0 : 1,
                has_next: false,
                has_previous: false,
              },
            },
          });
        }

        if (url.includes(`/knowledge-bases/${kbId}/tree`)) {
          return Response.json({
            success: true,
            data: { knowledge_base_id: kbId, folders: [] },
          });
        }

        if (
          url.includes(`/knowledge-bases/${kbId}`) &&
          !url.includes("/contents") &&
          !url.includes("/tree") &&
          !url.includes("/documents")
        ) {
          return Response.json({
            success: true,
            data: {
              id: kbId,
              name: "Policies KB",
              status: "active",
              default_language: "en",
              visibility_policy: "workspace",
              document_count: deleted ? 0 : 1,
              description: null,
              created_at: "2026-07-14T00:00:00Z",
              updated_at: "2026-07-14T12:00:00Z",
              version: 1,
            },
          });
        }

        if (url.includes(`/documents/${docId}`)) {
          return Response.json({
            success: true,
            data: {
              id: docId,
              title: "Employee Handbook",
              status: "active",
              declared_language: "en",
              classification_label: "public_internal",
              folder_id: null,
              current_version_id: "018f0000-0000-7000-8000-0000000000v1",
              tags: [],
              metadata: {},
              updated_at: "2026-07-14T12:00:00Z",
              created_at: "2026-07-14T00:00:00Z",
              version: 1,
            },
          });
        }

        return Response.json(
          { success: false, error: { code: "not_found", message: "missing" } },
          { status: 404 },
        );
      }),
    );

    renderBrowser();

    expect(await screen.findByText("Employee Handbook")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Delete Employee Handbook" }));
    expect(await screen.findByRole("heading", { name: "Delete Document" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: "Delete Document" })).not.toBeInTheDocument();
    });
    expect(deleted).toBe(false);

    await user.click(screen.getByRole("button", { name: "Delete Employee Handbook" }));
    await user.click(await screen.findByRole("button", { name: "Delete" }));

    expect(await screen.findByText(/Deleted/)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText("Employee Handbook")).not.toBeInTheDocument();
    });
    expect(deleted).toBe(true);
  });
});
