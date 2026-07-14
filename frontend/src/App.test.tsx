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

describe("chat module", () => {
  const kbId = "018f0000-0000-7000-8000-0000000000b1";
  const conversationId = "018f0000-0000-7000-8000-0000000000c1";

  function stubChatFetch(
    chatHandler?: (body: Record<string, unknown>) => Response,
  ): ReturnType<typeof vi.fn> {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (
        method === "GET" &&
        (url.includes("/knowledge-bases?") || url.endsWith("/knowledge-bases"))
      ) {
        return Response.json({
          success: true,
          data: {
            items: [
              {
                id: kbId,
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
              page_size: 100,
              total_items: 1,
              total_pages: 1,
              has_next: false,
              has_previous: false,
            },
          },
        });
      }
      if (method === "POST" && url.includes("/chat")) {
        const body = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>;
        if (chatHandler) {
          return chatHandler(body);
        }
        return Response.json({
          success: true,
          data: {
            conversation_id: conversationId,
            answer: "Annual leave is 20 working days [1].",
            citations: [
              {
                chunk_id: "018f0000-0000-7000-8000-0000000000d1",
                document_id: "018f0000-0000-7000-8000-0000000000e1",
                document_version_id: "018f0000-0000-7000-8000-0000000000f1",
                rank: 1,
                relevance_score: 0.91,
                excerpt: "Annual leave is 20 working days.",
                start_char: 0,
                end_char: 32,
                marker: "[1]",
              },
            ],
            retrieved_chunks: [
              {
                chunk_id: "018f0000-0000-7000-8000-0000000000d1",
                document_id: "018f0000-0000-7000-8000-0000000000e1",
                document_version_id: "018f0000-0000-7000-8000-0000000000f1",
                knowledge_base_id: kbId,
                score: 0.91,
                text: "Annual leave is 20 working days.",
                chunk_index: 0,
                start_char: 0,
                end_char: 32,
                heading: "Leave",
                language: "en",
              },
            ],
            abstained: false,
            status: "completed",
            abstention_reason: null,
            failure_reason: null,
            model_key: "gpt-4o-mini",
            prompt_template_version: "v1",
            warnings: [],
          },
        });
      }
      return Response.json(
        { success: false, error: { code: "not_found", message: "missing" } },
        { status: 404 },
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  afterEach(() => {
    window.sessionStorage.clear();
  });

  it("renders chat empty states and requires a knowledge base", async () => {
    stubChatFetch();
    renderApp("/chat");

    expect(await screen.findByRole("heading", { name: "Chat" })).toBeInTheDocument();
    expect(screen.getByText("No conversations yet")).toBeInTheDocument();
    expect(screen.getByText("Ask a question grounded in this knowledge base")).toBeInTheDocument();
    expect(screen.getByText("Evidence appears after each answer")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  });

  it("sends a chat turn and shows answer plus evidence", async () => {
    const user = userEvent.setup();
    const fetchMock = stubChatFetch();
    renderApp("/chat");

    await screen.findByRole("heading", { name: "Chat" });
    await user.click(screen.getByLabelText("Knowledge base"));
    await user.click(await screen.findByRole("option", { name: "Policies KB" }));

    const question = screen.getByLabelText("Question");
    await user.type(question, "How many leave days?");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByLabelText("Citation [1]")).toBeInTheDocument();
    expect(screen.getAllByText("completed").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Annual leave is 20 working days/).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Open document" }).length).toBeGreaterThan(0);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/chat"),
        expect.objectContaining({ method: "POST" }),
      );
    });

    expect(screen.getAllByText("How many leave days?").length).toBeGreaterThan(0);
    expect(screen.queryByText("No conversations yet")).not.toBeInTheDocument();
  });

  it("shows abstention banner when the turn abstains", async () => {
    const user = userEvent.setup();
    stubChatFetch(() =>
      Response.json({
        success: true,
        data: {
          conversation_id: conversationId,
          answer: null,
          citations: [],
          retrieved_chunks: [],
          abstained: true,
          status: "abstained",
          abstention_reason: "Insufficient supporting evidence",
          failure_reason: null,
          model_key: "gpt-4o-mini",
          prompt_template_version: "v1",
          warnings: [],
        },
      }),
    );
    renderApp("/chat");

    await screen.findByRole("heading", { name: "Chat" });
    await user.click(screen.getByLabelText("Knowledge base"));
    await user.click(await screen.findByRole("option", { name: "Policies KB" }));
    await user.type(screen.getByLabelText("Question"), "Secret formula?");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Abstained")).toBeInTheDocument();
    expect(screen.getByText("Insufficient supporting evidence")).toBeInTheDocument();
  });
});

describe("evaluation module", () => {
  const kbId = "018f0000-0000-7000-8000-0000000000b1";
  const runId = "run-eval-001";

  function stubEvaluationFetch(options?: {
    readonly empty?: boolean;
    readonly runsError?: boolean;
  }): ReturnType<typeof vi.fn> {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/knowledge-bases")) {
        return Response.json({
          success: true,
          data: {
            items: [
              {
                id: kbId,
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
              page_size: 100,
              total_items: 1,
              total_pages: 1,
              has_next: false,
              has_previous: false,
            },
          },
        });
      }
      if (url.includes("/evaluations/datasets")) {
        return Response.json({
          success: true,
          data: { items: options?.empty ? [] : ["kb-hr-fa-smoke"] },
        });
      }
      if (url.includes(`/evaluations/runs/${runId}`)) {
        return Response.json({
          success: true,
          data: {
            run_id: runId,
            config: {
              name: "smoke-topk8",
              top_k: 8,
              prompt_version: "v1",
              llm: "gpt-4o-mini",
              embedding_model: "BAAI/bge-m3",
              min_evidence_score: 0.25,
            },
            summary: {
              experiment_id: runId,
              status: "passed",
              failing_metrics: [],
              question_count: 10,
              error_count: 0,
            },
            metrics: {
              metrics: {
                retrieval: { recall_at_k: 0.84, mrr: 0.71 },
                generation: {
                  groundedness: 0.8,
                  citation_accuracy: 0.9,
                  citation_precision_mean: 0.88,
                },
                latency_ms: { retrieval_mean: 42, e2e_p95: 1100 },
              },
            },
          },
        });
      }
      if (url.includes("/evaluations/runs")) {
        if (options?.runsError) {
          return Response.json(
            {
              success: false,
              error: { code: "forbidden", message: "Permission denied" },
            },
            { status: 403 },
          );
        }
        if (options?.empty) {
          return Response.json({ success: true, data: { items: [] } });
        }
        return Response.json({
          success: true,
          data: {
            items: [
              {
                run_id: runId,
                name: "smoke-topk8",
                status: "passed",
                knowledge_base_id: kbId,
                dataset_id: "kb-hr-fa-smoke",
                dataset_version: "1.0.0",
                created_at: "2026-07-14T10:42:00Z",
                top_k: 8,
                prompt_version: "v1",
                llm: "gpt-4o-mini",
                failing_metrics: [],
                question_count: 10,
                error_count: 0,
                recall_at_k: 0.84,
                mrr: 0.71,
                groundedness: 0.8,
                citation_accuracy: 0.9,
                citation_precision_mean: 0.88,
                abstention_precision: 1,
                retrieval_latency_mean_ms: 42,
                e2e_p95_ms: 1100,
                e2e_p50_ms: 820,
                e2e_mean_ms: 900,
              },
            ],
          },
        });
      }
      return Response.json(
        { success: false, error: { code: "not_found", message: "missing" } },
        { status: 404 },
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  it("renders evaluation empty state when no runs exist", async () => {
    stubEvaluationFetch({ empty: true });
    renderApp("/evaluation");

    expect(await screen.findByRole("heading", { name: "Evaluation" })).toBeInTheDocument();
    expect(await screen.findByText("No evaluation runs yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New experiment" })).toBeInTheDocument();
  });

  it("renders metrics, trends, and recent runs", async () => {
    stubEvaluationFetch();
    renderApp("/evaluation");

    expect(await screen.findByRole("heading", { name: "Evaluation" })).toBeInTheDocument();
    expect(await screen.findByText("Overall quality")).toBeInTheDocument();
    expect(screen.getAllByText("Recall@K").length).toBeGreaterThan(0);
    expect(screen.getAllByText("0.84").length).toBeGreaterThan(0);
    expect(screen.getByText("Trend charts")).toBeInTheDocument();
    expect(screen.getAllByText("Groundedness").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Citation accuracy").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Retrieval latency").length).toBeGreaterThan(0);
    expect(await screen.findByText("smoke-topk8")).toBeInTheDocument();
    expect(await screen.findByText("Experiment summary")).toBeInTheDocument();
  });

  it("shows error state when runs fail to load", async () => {
    stubEvaluationFetch({ runsError: true });
    renderApp("/evaluation");

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/forbidden/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
