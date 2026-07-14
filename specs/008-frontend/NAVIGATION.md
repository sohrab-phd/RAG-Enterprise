# Navigation & Application Shell

> **Spec:** 008-frontend  
> **Authority:** Primary navigation, routes, and workspace shell

## Purpose

Provide a stable enterprise shell so users move between Knowledge, Chat, Evaluation, Experiments, and Settings without losing workspace context.

## Shell wireframe (desktop)

```text
┌──────────────────────────────────────────────────────────────────────┐
│ [Logo] RAG-enterprise          Workspace · HR Ops     Dev actor stub │
├────────────┬─────────────────────────────────────────────────────────┤
│            │  Breadcrumb: Knowledge / Policies KB / Leave Policy.pdf │
│ Knowledge  ├─────────────────────────────────────────────────────────┤
│ Chat       │                                                         │
│ Evaluation │                 Route outlet                            │
│ Experiments│                                                         │
│ Settings   │                                                         │
│            │                                                         │
│ ─────────  │                                                         │
│ Help (ext) │                                                         │
└────────────┴─────────────────────────────────────────────────────────┘
```

## Primary navigation

| Nav item | Route | Default landing |
| --- | --- | --- |
| Knowledge | `/knowledge` | KB list |
| Chat | `/chat` | New conversation (KB required) |
| Evaluation | `/evaluation` | Metrics overview |
| Experiments | `/experiments` | Run history |
| Settings | `/settings` | Providers |

### Secondary routes

| Route | Screen |
| --- | --- |
| `/knowledge` | Knowledge base list |
| `/knowledge/:kbId` | Knowledge browser (tree + detail) |
| `/knowledge/:kbId/documents/:documentId` | Document detail / metadata |
| `/knowledge/:kbId/documents/:documentId/versions/:versionId` | Version + processing status |
| `/chat` | Chat workspace |
| `/chat/:conversationId` | Resume conversation (client-held id from last chat response) |
| `/evaluation` | Evaluation overview |
| `/evaluation/runs/:runId` | Run summary (redirect or deep-link into Experiments) |
| `/experiments` | Experiment history |
| `/experiments/new` | Configure & start run |
| `/experiments/:runId` | Run detail / results |
| `/experiments/compare` | Side-by-side comparison (`?a=&b=`) |
| `/settings` | Settings hub |
| `/settings/providers` | Providers |
| `/settings/models` | Models |
| `/settings/prompts` | Prompt templates |
| `/settings/system` | System |

## Components (shell)

| Component | Role |
| --- | --- |
| `AppShell` | Header + sidebar + outlet |
| `PrimaryNav` | Module links with active state |
| `WorkspaceBadge` | Displays current workspace id/name |
| `Breadcrumbs` | Contextual path within module |
| `ActorStubBanner` | Non-prod notice: using `X-User-Id` / `X-Organization-Id` headers |

## States

| State | Behavior |
| --- | --- |
| Default | Sidebar expanded (240px), content fluid |
| Collapsed nav | Icon rail (72px); labels via tooltip |
| Missing workspace | Block outlet; message “Select workspace context” (config/env only in v1) |
| Route not found | Simple 404 page with link home |

## API endpoints

| Need | Endpoint | Notes |
| --- | --- | --- |
| Workspace label | Config / env in v1 | No workspace list API required yet |
| KB picker (shared) | `GET /api/v1/workspaces/{workspace_id}/knowledge-bases` | Used by Knowledge, Chat, Experiments |

## Loading

- Shell chrome renders immediately.
- Outlet shows module-level skeletons (do not blank the whole app).

## Errors

| Error | UI |
| --- | --- |
| Global API 401/403 | Inline banner: “Actor headers missing or forbidden” + link to Settings → System |
| Network down | Toast + retry on active query |

## Empty states

Not applicable to shell; modules own empties.

## Permission visibility (simple)

Hide or disable nav entries only when the API returns `forbidden` for that module’s first call. Do not build a full RBAC UI.

| Module | Soft gate permission (conceptual) |
| --- | --- |
| Knowledge | `knowledge_base:read` |
| Chat | `knowledge_base:read` |
| Evaluation / Experiments | `organization:evaluation:manage` |
| Settings | org admin / AI governance (when available) |

Until auth exists, all modules remain visible under the development actor stub.

## Deep linking rules

- URLs are the source of truth for selected KB, document, conversation, and experiment.
- Chat must not use a dedicated global chat overlay that breaks deep links.
- Evaluation run links open Experiments detail when artifacts exist.

## Non-goals

- Collapsible mega-menus
- Favorites / pin system
- Multi-org switcher
- Login modal
