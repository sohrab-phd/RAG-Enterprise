# RAG Generation

> **Status:** Implemented  
> **Spec:** [006 RAG Generation](../../specs/006-rag-generation/SPEC.md)

## Purpose

Produce grounded answers from retrieved chunks with citations, or abstain when
evidence is insufficient. No agents, tools, or function calling.

## Pipeline

```text
question (+ short history)
  → RetrievalService.retrieve()
  → evidence sufficiency gate
  → PromptBuilder (versioned template v1)
  → LLMProvider.complete()
  → citation validation
  → GenerationResult
```

## Package

```text
backend/src/rag_enterprise/generation/
  prompt_builder.py
  templates/v1.py
  providers/openai_compatible.py
  service.py
  persistence.py          # conversation + message
  repositories.py
  api/routes.py           # POST .../chat
```

## Chat API

`POST /api/v1/workspaces/{workspace_id}/chat`

Request:

```json
{
  "question": "سیاست مرخصی چیست؟",
  "knowledge_base_id": "...",
  "conversation_id": null,
  "top_k": 8
}
```

Response (`SuccessEnvelope`):

```json
{
  "success": true,
  "data": {
    "conversation_id": "...",
    "answer": "...",
    "citations": [{"chunk_id": "...", "marker": "[1]", "...": "..."}],
    "retrieved_chunks": [...],
    "abstained": false,
    "status": "completed"
  }
}
```

## LLM provider

Provider-agnostic factory (`create_llm_provider`). See [LLM Provider Layer (RC2.6)](LLM_PROVIDER_LAYER.md).

| `LLM_BACKEND` | Provider | Behavior |
| --- | --- | --- |
| `local` (default) | `ollama` | Local Ollama via `/api/chat` ([OLLAMA.md](OLLAMA.md)) |
| `api` | `openai` | OpenAI-compatible `POST {OPENAI_BASE_URL}/chat/completions` |
| `mock` | `echo` | Deterministic stub for CI (legacy `echo` behavior) |

Timeout: `LLM_TIMEOUT_SECONDS` (default 60s).

## Conversation history

- Tables: `conversation`, `message`
- Window: last 5–10 turns (default 6)
- No summarization / long-term memory

## Settings

| Env | Default |
| --- | --- |
| `LLM_BACKEND` | `local` |
| `LOCAL_PROVIDER` | `ollama` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` |
| `API_PROVIDER` | `openai` |
| `OPENAI_BASE_URL` | unset (required when `LLM_BACKEND=api`) |
| `OPENAI_API_KEY` | unset (required when `LLM_BACKEND=api`) |
| `LLM_MODEL_KEY` | `auto` |
| `GENERATION_MIN_EVIDENCE_SCORE` | `0.25` |
| `GENERATION_MAX_HISTORY_MESSAGES` | `6` |

Legacy: `echo`→`mock`, `http`→`api`; `LLM_BASE_URL` / `LLM_API_KEY` fill `OPENAI_*` when unset.

Startup validation rules: [CONFIGURATION.md](CONFIGURATION.md).

## Abstention policy (RC3.1)

Abstain paths (user always sees a clean localized message, never raw `ABSTAIN…`):

1. No retrieved chunks, or top score `< GENERATION_MIN_EVIDENCE_SCORE` (default **0.25** for real embeddings).
2. Model returns an abstain directive (robust parser; trailing junk/citations allowed).
3. Model returns echo-only / empty prose after sanitization.
4. Citation salvage fails (no chunks available after a substantive answer — rare).

When evidence already passed the score gate and the model answered without markers,
generation **salvages** a top-chunk citation instead of a false `citation_validation_failed`
abstain. See [RC3.1_FALSE_ABSTAIN_REPORT.md](../../RC3.1_FALSE_ABSTAIN_REPORT.md).

## Auth headers

Same as knowledge/retrieval: `X-User-Id`, `X-Organization-Id`.
