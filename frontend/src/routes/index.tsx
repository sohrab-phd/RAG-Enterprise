import { Navigate, type RouteObject } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { ChatPage } from "@/pages/chat-page";
import { EvaluationPage } from "@/pages/evaluation-page";
import { ExperimentsPage } from "@/pages/experiments-page";
import { KnowledgePage } from "@/pages/knowledge-page";
import { NotFoundPage } from "@/pages/not-found-page";
import { RouteErrorPage } from "@/pages/route-error-page";
import { SettingsPage } from "@/pages/settings-page";

export const appRoutes: RouteObject[] = [
  {
    path: "/",
    element: <AppShell />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <Navigate to="/knowledge" replace /> },
      { path: "knowledge", element: <KnowledgePage /> },
      { path: "knowledge/:kbId", element: <KnowledgePage /> },
      {
        path: "knowledge/:kbId/documents/:documentId",
        element: <KnowledgePage />,
      },
      {
        path: "knowledge/:kbId/documents/:documentId/versions/:versionId",
        element: <KnowledgePage />,
      },
      { path: "chat", element: <ChatPage /> },
      { path: "chat/:conversationId", element: <ChatPage /> },
      { path: "evaluation", element: <EvaluationPage /> },
      { path: "evaluation/runs/:runId", element: <EvaluationPage /> },
      { path: "experiments", element: <ExperimentsPage /> },
      { path: "experiments/new", element: <ExperimentsPage /> },
      { path: "experiments/compare", element: <ExperimentsPage /> },
      { path: "experiments/:runId", element: <ExperimentsPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "settings/providers", element: <SettingsPage /> },
      { path: "settings/models", element: <SettingsPage /> },
      { path: "settings/prompts", element: <SettingsPage /> },
      { path: "settings/system", element: <SettingsPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
