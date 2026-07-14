# Settings Module

> **Spec:** 008-frontend  
> **Authority:** Providers, models, prompt templates, and system inspection  
> **Constraint:** Read-mostly v1; do not redesign runtime config engines

## Module purpose

Give operators a clear view of **which AI and system settings the workspace is using**.  
v1 is primarily inspection + safe documentation of effective config. Editing is limited or deferred when only env-based config exists.

---

## Screen S1 — Settings hub

### Purpose

Entry points into settings sections.

### Wireframe

```text
┌─────────────────────────────────────────────┐
│ Settings                                    │
│ ○ Providers     Embedding + LLM backends    │
│ ○ Models        Model keys in use           │
│ ○ Prompts       Template versions           │
│ ○ System        Workspace / actor / health  │
└─────────────────────────────────────────────┘
```

### Components

`SettingsNav`, `SettingsCardLink`

### States / API / Loading / Errors / Empty

Static hub; no fetch until a sub-route.

---

## Screen S2 — Providers

### Purpose

Show embedding and LLM provider backends currently active.

### Wireframe

```text
┌────────────────────────────────────────────────────┐
│ Providers                                          │
│ Embedding                                          │
│   Backend: deterministic | flag                    │
│   Model: BAAI/bge-m3                               │
│   Status: available / unavailable                  │
│ LLM                                                │
│   Backend: echo | http                             │
│   Base URL: (masked if set)                        │
│   Status: available / unavailable                  │
│                                                    │
│ Note: Changes may require server config in v1.     │
└────────────────────────────────────────────────────┘
```

### Components

`ProviderCard`, `MaskedSecret`, `AvailabilityBadge`, `InfoCallout`

### States

| State | UI |
| --- | --- |
| Loading | Cards skeleton |
| Available | Green/neutral “available” text |
| Unavailable | Warning + last error snippet if API provides |
| Read-only | No save button when adapter is read-only |

### API endpoints

| Action | Planned thin adapter | Source today |
| --- | --- | --- |
| Get providers | `GET /api/v1/settings/providers` | Env: embedding + `LLM_BACKEND`, `LLM_BASE_URL` |

Secrets never returned in full.

### Loading / Errors / Empty

If adapter missing → callout “Settings API pending; see server env docs.”

---

## Screen S3 — Models

### Purpose

List model identifiers used by indexing and generation.

### Wireframe

```text
┌─────────────────────────────────────────────┐
│ Models                                      │
│ Embedding model id / name                   │
│ Generation model_key: gpt-4o-mini           │
│ Default top_k: 8                            │
│ min_evidence_score: 0.25                    │
└─────────────────────────────────────────────┘
```

### Components

`KeyValueList`, `ReadonlyField`

### States / API

| Action | Planned | Source |
| --- | --- | --- |
| Get models | `GET /api/v1/settings/models` | `LLM_MODEL_KEY`, embedding defaults, generation settings |

### Loading / Errors / Empty

Same as S2.

---

## Screen S4 — Prompt templates

### Purpose

Inspect versioned prompt templates used by generation (e.g. `v1`).

### Wireframe

```text
┌────────────────────────────────────────────────────┐
│ Prompt templates                                   │
│ Active: v1                                         │
│                                                    │
│ Preview (read-only)                                │
│ System: …                                          │
│ User template: …                                   │
│ Abstain message: …                                 │
│                                                    │
│ [Copy]                                             │
└────────────────────────────────────────────────────┘
```

### Components

`TemplateVersionSelect`, `CodeBlockReadonly`, `CopyButton`

### States

| State | UI |
| --- | --- |
| Loading | Preview skeleton |
| Missing version | Error |
| Multiple versions | Selector; only known shipped templates |

### API endpoints

| Action | Planned | Source |
| --- | --- | --- |
| List templates | `GET /api/v1/settings/prompts` | `generation/templates` |
| Get template | `GET /api/v1/settings/prompts/{version}` | e.g. `v1` |

Editing/publishing new templates is **out of scope for v1 UI** unless a future ADR adds prompt governance APIs.

### Loading / Errors / Empty

Empty only if no templates registered (should not happen once generation ships).

---

## Screen S5 — System

### Purpose

Show workspace context, actor stub headers, and API health.

### Wireframe

```text
┌────────────────────────────────────────────────────┐
│ System                                             │
│ Workspace id: …                                    │
│ Organization id (header): …                        │
│ User id (header): …                                │
│ API base URL: …                                    │
│ Health: [Check] → ok / degraded                    │
│                                                    │
│ Auth: not configured (dev actor headers)           │
│ Correlation demo: X-Correlation-ID                 │
└────────────────────────────────────────────────────┘
```

### Components

`SystemInfoList`, `HealthCheckButton`, `DevOnlyBanner`

### States

| State | UI |
| --- | --- |
| Health ok | Status text |
| Health fail | Error with status code |
| Headers missing | Warning pointing to how to set local env for Vite |

### API endpoints

| Action | Existing |
| --- | --- |
| Health | Platform health endpoint if present (e.g. `/api/v1/health`) |
| Settings context | Planned `GET /api/v1/settings/system` or client-config env |

### Loading / Errors / Empty

Health check is on-demand; no empty state.

## Module rules

1. **No authentication screens** (login, SSO, membership).
2. Do not store API keys in `localStorage`.
3. Mask secrets; show only last-4 or “configured / not configured.”
4. Prefer read-only until write APIs exist.
5. Keep copy boring and operational.

## Module non-goals

- Provider marketplace
- Multi-tenant billing settings
- Dark-mode marketing themes
- In-app secret rotation workflows
