# Ollama Local LLM (RC2.7)

> **Status:** Implemented  
> **Scope:** `OllamaProvider` only. GenerationService, PromptBuilder, Retrieval,
> Chunking, Embeddings, Evaluation, and public chat contracts are unchanged.

Default path when `LLM_BACKEND=local` and `LOCAL_PROVIDER=ollama`.

## Architecture

```text
GenerationService
       │  LLMProvider protocol only
       ▼
 create_llm_provider(settings)
       │
       ▼
 LocalProvider → OllamaProvider → Ollama HTTP API
```

Nothing outside the provider factory imports or configures Ollama.

## Install Ollama

1. Install from [https://ollama.com](https://ollama.com) for your OS.
2. Confirm the daemon listens on the configured base URL (default `http://localhost:11434`):

```bash
curl http://localhost:11434/api/tags
```

3. Pull at least one chat model (example — replace with any model you prefer):

```bash
ollama pull gemma4:e4b-it-qat
```

Never hardcode model names in application code. Discovery always uses `GET /api/tags`.

## Configuration

| Env | Default | Notes |
|-----|---------|-------|
| `LLM_BACKEND` | `local` | Must be `local` for Ollama |
| `LOCAL_PROVIDER` | `ollama` | Only `ollama` in V1 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | No hardcoded URL outside settings |
| `LLM_MODEL_KEY` | `auto` | Explicit name, `auto`, or empty (= `auto`) |
| `LLM_TIMEOUT_SECONDS` | `60` | Shared completion timeout |

Example `backend/.env` snippet:

```bash
LLM_BACKEND=local
LOCAL_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL_KEY=auto
LLM_TIMEOUT_SECONDS=120
```

## Model selection

| `LLM_MODEL_KEY` | Behavior |
|-----------------|----------|
| Explicit name (e.g. `gemma4:e4b-it-qat`) | Must exist in `/api/tags`; otherwise **startup fails** with requested + installed list and fix steps |
| `auto` or empty | If one model → select it. If multiple → select first alphabetically and emit a **startup warning** (does not fail). If none → **startup fails** |

To change models deterministically:

```bash
ollama pull <other-model>
# then set:
LLM_MODEL_KEY=<other-model>
```

Restart the backend after changing env or pulling models so selection re-runs.

## Generation

Uses official non-streaming chat:

`POST {OLLAMA_BASE_URL}/api/chat`

- System prompt and user prompt from PromptBuilder (unchanged)
- Conversation history is already embedded in the user prompt by PromptBuilder
- Temperature and timeout honored
- UTF-8 / Persian (including ZWNJ) preserved — no extra normalization on prompts or evidence

HTTP client is reused per provider instance (thread-safe under asyncio).

## Health and inventory

| Endpoint | Behavior when `LLM_BACKEND=local` |
|----------|-----------------------------------|
| `GET /api/v1/ready` | Probes reachability, installed models, selected model, lightweight generation ping; exposes `response_time_ms` in the `llm` check detail. Unavailable Ollama → **not_ready** |
| `GET /api/v1/system` | `llm.backend`, `llm.provider`, `llm.selected_model`, `llm.installed_models`, `llm.timeout_seconds`, `llm.ollama_version` (if available) |
| `GET /api/v1/system/models` | Developer catalog: backend, provider, selection_mode, selected_model, installed_models, base_url, reachable |

If Ollama is unreachable at startup, the API process still starts (degraded). Ready checks fail until Ollama is up. Fatal config errors (no models / explicit model missing) exit startup with a structured message.

## Startup log

On successful discovery you should see a block similar to:

```text
--------------------------------------------
LLM Backend
local

Provider
ollama

Base URL
http://localhost:11434

Installed Models
4

Selected Model
gemma4:e4b-it-qat

Selection Mode
auto
--------------------------------------------
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Ready `llm` check fails / connection refused | Daemon not running | Start Ollama; verify `OLLAMA_BASE_URL` |
| Startup: no models installed | Empty `/api/tags` | `ollama pull <model>` |
| Startup: requested model missing | Wrong `LLM_MODEL_KEY` | Pull the model or set `LLM_MODEL_KEY=auto` |
| Multiple-models warning | Several tags installed | Set `LLM_MODEL_KEY=<exact-name>` |
| Timeouts on chat | Cold model / slow hardware | Raise `LLM_TIMEOUT_SECONDS`; warm with a small chat once |
| Persian garbling | Client encoding | Ensure UTF-8 end-to-end; do not post-normalize RAG evidence |

## Related

- [LLM Provider Layer (RC2.6)](LLM_PROVIDER_LAYER.md)
- [RAG Generation](RAG_GENERATION.md)
- [Configuration](CONFIGURATION.md)
- [Operational Health](OPERATIONAL_HEALTH.md)
- [FIRST_RUN](../FIRST_RUN.md)
