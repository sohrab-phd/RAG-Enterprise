# Frontend — RAG-enterprise Platform

> **Spec ID:** 008  
> **Status:** Draft — design only, no implementation  
> **Goal:** Define the enterprise web console for Knowledge, Chat, Evaluation, Experiments, and Settings.  
> **Stack (when implemented):** React, Vite, TypeScript, Tailwind, shadcn/ui (ADR-004)

## Purpose

RAG-enterprise is an **enterprise knowledge and RAG operations platform**, not a consumer chatbot.

Operators:

1. Curate and process knowledge corpora
2. Ask grounded questions with full evidence visibility
3. Measure quality via offline evaluation
4. Compare experiment runs
5. Inspect system AI configuration

This spec designs screens, navigation, components, responsive behavior, and API mapping.  
**It does not implement UI code.**

## Product principles

| Principle | Rule |
| --- | --- |
| Platform, not chat clone | Primary IA is module navigation; Chat is one module |
| Evidence first | Answers always expose citations, retrieved chunks, scores, and failure/abstain reasons |
| Backend-faithful | UI consumes existing `/api/v1` contracts; no backend redesign |
| Simple | Prefer list + detail layouts; no analytics dashboards or chart libraries in v1 |
| Desktop first | Full workflows on desktop; tablet supported; mobile optional/read-mostly |
| No authentication product | Identity UI is out of scope; use existing dev actor headers |

## Modules

| Module | Primary job | Spec |
| --- | --- | --- |
| Knowledge | Tree, upload, metadata, processing status | [KNOWLEDGE.md](KNOWLEDGE.md) |
| Chat | Conversation, prompt, evidence panel | [CHAT.md](CHAT.md) |
| Evaluation | Metrics overview and recent runs | [EVALUATION.md](EVALUATION.md) |
| Experiments | Config, history, comparison, results | [EXPERIMENTS.md](EXPERIMENTS.md) |
| Settings | Providers, models, prompts, system | [SETTINGS.md](SETTINGS.md) |

## Spec map

| Document | Contents |
| --- | --- |
| [NAVIGATION.md](NAVIGATION.md) | Shell, routes, workspace context, permissions |
| [KNOWLEDGE.md](KNOWLEDGE.md) | Knowledge screens |
| [CHAT.md](CHAT.md) | Chat / evidence screens |
| [EVALUATION.md](EVALUATION.md) | Evaluation overview screens |
| [EXPERIMENTS.md](EXPERIMENTS.md) | Experiment run screens |
| [SETTINGS.md](SETTINGS.md) | Settings screens |
| [COMPONENTS.md](COMPONENTS.md) | Shared components and design tokens |
| [RESPONSIVE.md](RESPONSIVE.md) | Breakpoints and layout rules |
| [API_MAPPING.md](API_MAPPING.md) | Screen → endpoint mapping and API gaps |
| [ACCEPTANCE.md](ACCEPTANCE.md) | Given/When/Then acceptance |

## Non-goals

| Out of scope | Reason |
| --- | --- |
| Implementing React/HTML/CSS | Design-only deliverable |
| Authentication / login / SSO UI | Separate identity work; not this phase |
| Backend API redesign | Use Features 001–007 as-is |
| Chart libraries / marketing dashboards | Evaluation shows metric numbers, not charts |
| Mobile-first consumer chat | ChatGPT-style full-screen chat is rejected |
| Multi-workspace switcher productization | Soft-assume single workspace from env/header |
| Optimization / auto-tune UI | Experiments measure; they do not auto-select winners |

## Information architecture (high level)

```text
┌─────────────────────────────────────────────────────────────┐
│  RAG-enterprise          Workspace: {name}     Actor stub   │
├──────────┬──────────────────────────────────────────────────┤
│ Knowledge│  Module content (list / tree / detail / panel)   │
│ Chat     │                                                  │
│ Eval     │                                                  │
│ Experiments                                                 │
│ Settings │                                                  │
└──────────┴──────────────────────────────────────────────────┘
```

## Design posture

- Dense, calm enterprise UI (tables, trees, status chips, side panels)
- Status always visible as text + tone (never color alone)
- Loading / empty / error states required on every screen (see per-screen specs)
- Persian and English content supported in display; layout remains LTR shell in v1 (content can be RTL inside text regions)

## Dependencies on backend

| Capability | Backend status | Frontend readiness |
| --- | --- | --- |
| Knowledge CRUD + upload + status | Implemented HTTP | Ready |
| Chat grounded answer | Implemented HTTP | Ready |
| Retrieval (for debug evidence) | Implemented HTTP | Ready (optional advanced panel) |
| Evaluation metrics / runs | Engine exists; **no HTTP yet** | Needs thin read API adapter (see API_MAPPING) |
| Settings (providers/models/prompts) | Env / config today | Needs thin read API adapter (see API_MAPPING) |

Thin adapters expose existing services/artifacts. They must not change RAG pipeline behavior.

## Related documents

- [001 Knowledge Management](../001-knowledge-management/README.md)
- [005 Retrieval](../005-retrieval/SPEC.md)
- [006 RAG Generation](../006-rag-generation/SPEC.md)
- [007 Evaluation Framework](../007-evaluation-framework/README.md)
- [Frontend rules](../../.cursor/rules/frontend.md)
- [ADR-004 Frontend selection](../../docs/adr/004-frontend-selection.md)
