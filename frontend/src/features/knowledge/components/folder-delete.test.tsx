import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ThemeProvider } from "@/components/theme/theme-provider";
import { appRoutes } from "@/routes";

const kbId = "018f0000-0000-7000-8000-0000000000b1";
const folderId = "018f0000-0000-7000-8000-0000000000f1";
const keepFolderId = "018f0000-0000-7000-8000-0000000000f2";

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

describe("folder deletion", () => {
  it("shows trash, confirms, cancels, deletes, toasts, and refreshes", async () => {
    const user = userEvent.setup();
    let deleted = false;

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = (init?.method ?? "GET").toUpperCase();

        if (method === "DELETE" && url.includes(`/folders/${folderId}`)) {
          deleted = true;
          return new Response(null, { status: 204 });
        }

        if (url.includes(`/knowledge-bases/${kbId}/contents`)) {
          return Response.json({
            success: true,
            data: {
                    folders: deleted
                ? [
                    {
                      id: keepFolderId,
                      name: "Policies",
                      status: "active",
                      parent_folder_id: null,
                      path: "/Policies",
                      depth: 0,
                      version: 1,
                    },
                  ]
                : [
                    {
                      id: folderId,
                      name: "Human Resources",
                      status: "active",
                      parent_folder_id: null,
                      path: "/Human Resources",
                      depth: 0,
                      version: 1,
                    },
                    {
                      id: keepFolderId,
                      name: "Policies",
                      status: "active",
                      parent_folder_id: null,
                      path: "/Policies",
                      depth: 0,
                      version: 1,
                    },
                  ],
              documents: [],
              pagination: {
                page: 1,
                page_size: 50,
                total_items: 0,
                total_pages: 0,
                has_next: false,
                has_previous: false,
              },
            },
          });
        }

        if (url.includes(`/knowledge-bases/${kbId}/tree`)) {
          return Response.json({
            success: true,
            data: {
              knowledge_base_id: kbId,
              folders: deleted
                ? [
                    {
                      id: keepFolderId,
                      name: "Policies",
                      status: "active",
                      document_count: 0,
                      children: [],
                    },
                  ]
                : [
                    {
                      id: folderId,
                      name: "Human Resources",
                      status: "active",
                      document_count: 1,
                      children: [],
                    },
                    {
                      id: keepFolderId,
                      name: "Policies",
                      status: "active",
                      document_count: 0,
                      children: [],
                    },
                  ],
            },
          });
        }

        if (
          url.includes(`/knowledge-bases/${kbId}`) &&
          !url.includes("/contents") &&
          !url.includes("/tree") &&
          !url.includes("/folders") &&
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

        return Response.json(
          { success: false, error: { code: "not_found", message: "missing" } },
          { status: 404 },
        );
      }),
    );

    renderBrowser();

    expect((await screen.findAllByText("Human Resources")).length).toBeGreaterThanOrEqual(1);

    const trashButtons = await screen.findAllByRole("button", {
      name: "Delete folder Human Resources",
    });
    expect(trashButtons.length).toBeGreaterThanOrEqual(1);

    await user.click(trashButtons[0]);
    expect(await screen.findByRole("heading", { name: "Delete Folder?" })).toBeInTheDocument();
    expect(screen.getByText(/Folder:\s*Human Resources/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: "Delete Folder?" })).not.toBeInTheDocument();
    });
    expect(deleted).toBe(false);

    await user.click(screen.getAllByRole("button", { name: "Delete folder Human Resources" })[0]);
    await user.click(await screen.findByRole("button", { name: "Delete" }));

    expect(await screen.findByText(/Deleted/)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryAllByText("Human Resources")).toHaveLength(0);
    });
    expect(screen.getAllByText("Policies").length).toBeGreaterThanOrEqual(1);
    expect(deleted).toBe(true);
  });
});
