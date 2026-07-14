# RAG-enterprise Frontend

> **Release:** 1.0.0 (`package.json` version)

Enterprise operator console (Feature 008). Knowledge, Chat, and Evaluation dashboard
are implemented; Experiments / Settings remain placeholders.

## Purpose

UI for operators to manage knowledge bases, run grounded chat, and inspect
evaluation runs against the FastAPI backend.

## Stack

- React 19 + Vite + TypeScript
- Tailwind CSS v4 + shadcn/ui
- React Router · TanStack Query · React Hook Form + Zod

## Implemented

- App shell (header, sidebar, layout, theme, routing)
- Knowledge module against real `/api/v1` endpoints (including **Publish** and **Process & Index**)
- Chat module (`POST .../chat`) with citations and evidence/pipeline panels
- Evaluation dashboard (Feature 007 read adapters + trend charts)

## Prerequisites

- Node.js 20+ and npm
- Backend running locally (see [backend/README.md](../backend/README.md))

## Setup

```bash
npm ci
```

## Run

```bash
npm run dev
```

Env defaults (match backend knowledge fixtures unless overridden):

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

## Related documents

- [Documentation index](../docs/README.md)
- [Feature Map](../docs/FEATURE_MAP.md)
- [Demo Guide](../docs/DEMO_GUIDE.md)
- [Spec 008](../specs/008-frontend/README.md)
- [Development Guide](../docs/DEVELOPMENT.md)
- [Root README](../README.md)
