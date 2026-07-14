# Chat Module

> **Spec:** 008-frontend  
> **Authority:** Conversation, prompt, evidence, citations, and retrieval diagnostics

## Module purpose

Support grounded Q&A over a selected knowledge base with an **evidence panel** equal in priority to the answer. This is an operator console for verifying RAG quality—not a consumer ChatGPT clone.

---

## Screen C1 — Chat workspace

### Purpose

Ask questions, view answers/abstentions, and inspect supporting evidence.

### Wireframe (desktop)

```text
┌────────────────────┬──────────────────────────────┬─────────────────────────┐
│ Conversations      │ Chat                         │ Evidence                │
│                    │ KB: [Policies KB ▾]  top_k:8  │                         │
│ • Leave policy     │──────────────────────────────│ Citations               │
│ • Benefits FAQ     │ User: مرخصی سالانه چند روز؟  │ [1] Leave Policy · 0.91 │
│ [+ New]            │                              │ [2] Handbook · 0.84     │
│                    │ Assistant: ۲۰ روز کاری [1]   │                         │
│                    │ status: completed            │ Retrieved chunks        │
│                    │ model: gpt-4o-mini  · 820ms  │ #1 score 0.91           │
│                    │                              │ Annual leave is 20…     │
│                    │──────────────────────────────│ #2 score 0.84           │
│                    │ [Ask about this KB_________] │                         │
│                    │ [Send]                       │ Latency                 │
│                    │                              │ e2e ~820ms (client)     │
└────────────────────┴──────────────────────────────┴─────────────────────────┘
```

Three panes: **History | Conversation | Evidence**.

### Components

`ChatLayout`, `ConversationList`, `MessageThread`, `PromptComposer`, `KnowledgeBaseSelect`, `TopKSelect`, `EvidencePanel`, `CitationList`, `RetrievedChunkList`, `SimilarityBar`, `LatencyMeta`, `AbstentionBanner`, `WarningChips`

### States

| State | UI |
| --- | --- |
| No KB selected | Composer disabled; Evidence empty; prompt “Select a knowledge base” |
| Idle | Empty thread for new conversation |
| Submitting | Composer disabled; assistant placeholder “Retrieving and generating…” |
| Completed | Answer + citations highlighted; Evidence synced to last turn |
| Abstained | Distinct banner with `abstention_reason`; no fake “helpful” answer styling |
| Failed | Error card with `failure_reason` / envelope code; Retry last question |
| Stale conversation | If POST fails mid-flight, keep prior messages; show error on pending turn |

### API endpoints

| Action | Method / path |
| --- | --- |
| Ask | `POST /api/v1/workspaces/{workspace_id}/chat` |
| Optional diagnose retrieve | `POST /api/v1/workspaces/{workspace_id}/retrieve` |

**Chat request fields used:** `question`, `knowledge_base_id`, `conversation_id`, `top_k`, `language_hint`, optional `document_ids`.

**Chat response fields shown:** `answer`, `citations`, `retrieved_chunks`, `abstained`, `status`, `abstention_reason`, `failure_reason`, `model_key`, `prompt_template_version`, `warnings`, `conversation_id`.

### Loading

- Optimistic user bubble immediately.
- Assistant area: progress text (no fake streamed tokens unless backend adds streaming later).
- Evidence panel shows loading skeleton only for the active turn.

### Errors

| Condition | UI |
| --- | --- |
| `validation_failed` | Inline under composer |
| `forbidden` / missing actor | Shell banner |
| Retrieval/generation failure in payload | Failed turn card |
| Timeout / network | Retry button; do not duplicate messages |

### Empty states

| Area | Copy |
| --- | --- |
| Conversation list | “No conversations yet. Ask a question to start.” |
| Thread | “Ask a question grounded in this knowledge base.” |
| Evidence (before first answer) | “Evidence appears after each answer.” |

### Conversation list note (v1)

Backend persists conversations but may not expose a list endpoint yet.  
v1 UI options (pick one during implementation; prefer simplest):

1. **Client session list** — store `{conversation_id, title, kb_id, updated_at}` in memory / `sessionStorage` from chat responses.
2. **Planned thin** `GET .../conversations` adapter later.

Do not invent local-only fake answers.

---

## Screen C2 — Evidence panel (detail interactions)

### Purpose

Inspect citations and retrieved chunks for the selected assistant turn.

### Wireframe (panel sections)

```text
┌─ Evidence ──────────────────────────┐
│ Turn: latest / selected             │
│ Status: completed | abstained       │
│ Model · Prompt v1 · Latency         │
│─────────────────────────────────────│
│ Citations                           │
│ [1] rank 1 · score 0.91             │
│     excerpt…                        │
│     doc Leave Policy.pdf            │
│─────────────────────────────────────│
│ Retrieved chunks (top_k)            │
│ 1. 0.91  Leave Policy               │
│    text preview                     │
│ 2. 0.84  Handbook                   │
└─────────────────────────────────────┘
```

### Components

`CitationCard`, `ChunkRow`, `ScoreMeter` (text + bar), `MarkerChip` (`[1]`)

### Interactions

| Action | Behavior |
| --- | --- |
| Click citation marker in answer | Scroll/highlight matching citation and chunk |
| Click chunk row | Expand full text; highlight if cited |
| Click document title | Navigate to Knowledge document detail |

### Similarity

Show `relevance_score` / retrieve `score` as numeric (e.g. `0.91`) plus a compact bar. No chart library.

### Latency

| Metric | Source |
| --- | --- |
| Client e2e | Browser timing of chat request |
| Server timings | Not in chat DTO today → omit or show “—” until available |

### States

| State | UI |
| --- | --- |
| Abstained | Citations empty; show reason; still list retrieved chunks if returned |
| Failed | Panels cleared for that turn; show failure reason |
| No chunks | “No chunks retrieved.” |

### API endpoints

Uses last `ChatResponseDTO`. Optional refresh via `POST .../retrieve` with same question/KB/`top_k` for debug re-fetch (label as “Re-run retrieval”).

### Loading / Errors / Empty

As Screen C1.

---

## Chat UX rules (anti–ChatGPT-clone)

1. Evidence panel is always visible on desktop (≥1280px).
2. Answer area is never full-viewport-only.
3. Status (`completed` / `abstained` / `failed`) is always labeled.
4. No personality branding, starter prompt gallery, or “surprise me”.
5. KB selector is mandatory before send.

## Module non-goals

- Streaming SSE UI (until backend supports it)
- File attachments in chat
- Agents / tools / browsing
- Multi-KB federated chat
- Voice input
