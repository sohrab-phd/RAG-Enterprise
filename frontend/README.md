# RAG-enterprise Frontend

Enterprise operator console shell (Feature 008). Business modules are placeholders only.

## Stack

- React 19 + Vite + TypeScript
- Tailwind CSS v4 + shadcn/ui
- React Router
- TanStack Query

## What's implemented

- App shell (header, sidebar, layout)
- Primary navigation (Knowledge, Chat, Evaluation, Experiments, Settings)
- Theme (light/dark) + IBM Plex fonts
- Routing + nested placeholder routes
- Loading layout (Suspense fallback)
- Error boundary + route error page
- 404 page
- Actor stub banner (no auth UI)

## Setup

```bash
npm install
```

## Development

```bash
npm run dev
```

Optional env:

```bash
VITE_WORKSPACE_NAME="HR Ops"
VITE_API_BASE_URL=http://localhost:8000
```

## Quality

```bash
npm run lint
npm run format:check
npm run test
npm run build
```

## Spec

See [`specs/008-frontend/`](../specs/008-frontend/README.md).
