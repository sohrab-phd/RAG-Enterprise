# Acceptance Criteria — Frontend Design

> **Spec:** 008-frontend  
> **Authority:** Given/When/Then for the console design (pre-implementation)

## AC-01: Enterprise IA (not a chat clone)

**Given** a user opens the application  
**When** the shell loads  
**Then** primary navigation includes Knowledge, Chat, Evaluation, Experiments, and Settings  
**And** Chat is one module among equals, not the sole full-screen product surface  
**And** on desktop Chat always shows an Evidence panel alongside the thread

---

## AC-02: Knowledge tree and list

**Given** a workspace with at least one knowledge base  
**When** the user opens Knowledge and selects a KB  
**Then** they see a folder tree, document list, and document inspector  
**And** APIs used are existing Knowledge list/get endpoints  
**And** empty folders show an empty state with Upload CTA

---

## AC-03: Upload and processing status

**Given** a user uploads a file into a folder  
**When** the upload session completes and a version is created  
**Then** processing status is visible and pollable via version status API  
**And** indexed / failed / processing states are labeled with text (not color alone)  
**And** retry appears only when the API marks the failure retryable

---

## AC-04: Document metadata

**Given** a selected document  
**When** the user edits title, language, tags, or metadata and saves  
**Then** the UI calls existing patch/metadata endpoints  
**And** validation errors map to fields  
**And** archived documents are read-only

---

## AC-05: Grounded chat with evidence

**Given** a knowledge base is selected  
**When** the user sends a question  
**Then** the UI calls `POST .../chat`  
**And** the Evidence panel shows citations, retrieved chunks, and similarity scores from the response  
**And** abstention and failure statuses are distinct from completed answers  
**And** the composer is disabled until a KB is selected

---

## AC-06: Evaluation overview

**Given** evaluation run artifacts are available via API adapter (or empty if not)  
**When** the user opens Evaluation  
**Then** they see overall metric tiles (Recall@K, MRR, Groundedness, Citation Precision, Abstention Precision, latency)  
**And** recent runs are listed with pass/fail  
**And** no charts are rendered  
**And** if the adapter is missing, the empty state explains the pending API (no fabricated metrics)

---

## AC-07: Experiments configure and results

**Given** an operator creates a new experiment with dataset version, top_k, prompt version, and thresholds  
**When** the run completes  
**Then** the detail view shows frozen config, aggregate metrics, and per-question results  
**And** failing threshold names are listed when status is failed  
**And** configuration matches Feature 007 experiment fields (no redesigned knobs)

---

## AC-08: Experiment comparison

**Given** two completed runs  
**When** the user opens Compare and selects run A and run B  
**Then** metric values are shown side by side with deltas  
**And** config differences are listed  
**And** mismatched datasets show a caution warning

---

## AC-09: Settings read-only inspection

**Given** the Settings module  
**When** the user opens Providers, Models, Prompts, or System  
**Then** effective configuration is displayed when adapters exist  
**And** secrets are masked  
**And** no authentication/login UI is present  
**And** write/edit of production providers is not required in v1

---

## AC-10: Responsive policy

**Given** desktop (≥1280px) and tablet (768–1023px) viewports  
**When** Knowledge and Chat layouts adapt  
**Then** desktop preserves multi-pane workflows  
**And** tablet collapses secondary panes into drawers/tabs  
**And** mobile is optional with a “best on desktop” notice for heavy flows

---

## AC-11: Loading, error, empty everywhere

**Given** any primary screen (K1–K5, C1, E1, X1–X4, S2–S5)  
**When** data is loading, empty, or failed  
**Then** the screen defines an explicit loading, empty, and error presentation  
**And** mutating actions prevent double submit

---

## AC-12: Backend fidelity

**Given** this frontend design  
**When** implementation begins  
**Then** Knowledge and Chat use existing HTTP contracts without backend redesign  
**And** Evaluation/Experiments/Settings only introduce thin expose adapters over Feature 007 and config  
**And** authentication product work remains out of scope

---

## AC-13: API mapping completeness

**Given** [API_MAPPING.md](API_MAPPING.md)  
**When** reviewing a screen  
**Then** each screen lists existing endpoints or an explicit gap  
**And** gaps do not invent new RAG behavioral APIs (no new ranking/generation semantics)

---

## Out of scope checks (must remain false for v1)

| Capability | Required absent |
| --- | --- |
| ChatGPT-style starter home | Yes absent |
| Metrics charts library | Yes absent |
| Login / SSO screens | Yes absent |
| Auto-optimize experiment UI | Yes absent |
| Backend pipeline redesign | Yes absent |
