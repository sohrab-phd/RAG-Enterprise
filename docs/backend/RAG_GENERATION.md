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

`OpenAICompatibleLLMProvider`:

| `LLM_BACKEND` | Behavior |
| --- | --- |
| `echo` (default) | Deterministic local completion for CI/dev |
| `http` | OpenAI-compatible `POST {LLM_BASE_URL}/chat/completions` |

Timeout: `LLM_TIMEOUT_SECONDS` (default 60s).

## Conversation history

- Tables: `conversation`, `message`
- Window: last 5–10 turns (default 6)
- No summarization / long-term memory

## Settings

| Env | Default |
| --- | --- |
| `LLM_BACKEND` | `echo` |
| `LLM_MODEL_KEY` | `gpt-4o-mini` |
| `GENERATION_MIN_EVIDENCE_SCORE` | `0.25` |
| `GENERATION_MAX_HISTORY_MESSAGES` | `6` |

## Auth headers

Same as knowledge/retrieval: `X-User-Id`, `X-Organization-Id`.
