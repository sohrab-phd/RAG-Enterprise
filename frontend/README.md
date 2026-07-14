# RAG-enterprise Frontend

Enterprise operator console (Feature 008). Knowledge (Sprint 1), Chat (Sprint 2), and Evaluation dashboard (Sprint 3).

## Stack

- React 19 + Vite + TypeScript
- Tailwind CSS v4 + shadcn/ui
- React Router
- TanStack Query
- React Hook Form + Zod

## Implemented

- App shell (header, sidebar, layout, theme, routing)
- Knowledge module against real `/api/v1` endpoints:
  - Knowledge base list / create
  - Browser: folder tree, document list, inspector
  - Upload dialog with drag-and-drop + progress
  - Metadata edit drawer
  - Processing status from create-version response
- Chat module against `POST /api/v1/workspaces/{workspace_id}/chat`:
  - Conversation list (client `sessionStorage` until a list API exists)
  - Thread, prompt composer (KB + top_k), citations
  - Evidence panel and Pipeline Inspector (optional `POST .../retrieve`)
  - Loading / empty / error / abstention states
  - Streaming-ready turn state (`pending` → `complete`); SSE not implemented
- Evaluation dashboard against Feature 007 read adapters:
  - Overview metrics, failing gates, recent runs, run detail/summary
  - Trend charts: Groundedness, Recall@K, Citation accuracy, Retrieval latency
  - KB / dataset filters; empty / loading / error states
- Experiments / Settings remain placeholders

## Setup

```bash
npm install
```

## Development

```bash
npm run dev
```

Env (defaults match backend knowledge test fixtures):

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WORKSPACE_ID=018f0000-0000-7000-8000-000000000002
VITE_ORGANIZATION_ID=018f0000-0000-7000-8000-000000000001
VITE_USER_ID=018f0000-0000-7000-8000-000000000003
VITE_WORKSPACE_NAME="HR Ops"
```

Dev proxy: `/api` → `VITE_API_BASE_URL` or `http://localhost:8000`.

## Quality

```bash
npm run lint
npm run format:check
npm run test
npm run build
```

## Spec

See [`specs/008-frontend/`](../specs/008-frontend/README.md).
