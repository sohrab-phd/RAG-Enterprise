# LLM Provider Layer (RC2.6 / RC2.7)

> **Status:** Implemented  
> **Scope:** Provider subsystem only — GenerationService, PromptBuilder, Retrieval, and
> chat APIs are unchanged. Local Ollama generate is implemented in RC2.7.

## Architecture

```text
GenerationService
       │  depends only on LLMProvider (protocol)
       ▼
 create_llm_provider(settings)   ← sole construction site
       │
       ├── LLM_BACKEND=local  → LocalProvider / OllamaProvider
       ├── LLM_BACKEND=api    → APIProvider / OpenAICompatibleProvider
       └── LLM_BACKEND=mock   → MockProvider (legacy echo behavior)
```

| Backend | Provider (V1) | Purpose |
|---------|---------------|---------|
| **local** (default) | `ollama` | On-machine chat via Ollama (`/api/tags`, `/api/chat`) |
| **api** | `openai` | OpenAI-compatible `POST {base}/chat/completions` |
| **mock** | `echo` | Deterministic stub for CI / offline demos — **not** recommended as default |

## Configuration

| Env | Default | Notes |
|-----|---------|-------|
| `LLM_BACKEND` | `local` | `local` \| `api` \| `mock` |
| `LOCAL_PROVIDER` | `ollama` | Only `ollama` in V1 |
| `API_PROVIDER` | `openai` | Only `openai` in V1 |
| `MOCK_PROVIDER` | `echo` | Only `echo` in V1 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Required for `local` |
| `OPENAI_BASE_URL` | unset | Required for `api` |
| `OPENAI_API_KEY` | unset | Required for `api` |
| `LLM_MODEL_KEY` | `auto` | For local: discover via `/api/tags`; empty ≡ `auto`. For api: concrete model id |
| `LLM_TIMEOUT_SECONDS` | `60` | Shared timeout |

Full local setup: [OLLAMA.md](OLLAMA.md).

### Backward compatibility

| Legacy | Maps to | Warning |
|--------|---------|---------|
| `LLM_BACKEND=echo` | `mock` | `echo/http are deprecated; use local/api/mock.` |
| `LLM_BACKEND=http` | `api` | same |
| `LLM_BASE_URL` / `LLM_API_KEY` | fill `OPENAI_*` when unset | Prefer `OPENAI_*` |

## Health / system

When `LLM_BACKEND=local`, `GET /api/v1/ready` includes an `llm` check (reachability,
models, selected model, generation ping, `response_time_ms`).

`GET /api/v1/system` includes:

```json
"llm": {
  "backend": "local",
  "provider": "ollama",
  "model": "gemma4:e4b-it-qat",
  "selected_model": "gemma4:e4b-it-qat",
  "installed_models": ["gemma4:e4b-it-qat"],
  "timeout_seconds": 60.0,
  "ollama_version": "0.9.0",
  "selection_mode": "auto",
  "reachability": "reachable"
}
```

`GET /api/v1/system/models` returns the developer model catalog
(`backend`, `provider`, `selection_mode`, `selected_model`, `installed_models`,
`base_url`, `reachable`).

## Package layout

```text
generation/providers/
  factory.py              # create_llm_provider / describe_llm_runtime / probe_llm_provider
  local.py / api.py       # category bases
  ollama.py               # LocalProvider implementation (RC2.7)
  openai_compatible.py    # API OpenAI-compatible client
  mock.py                 # echo MockProvider
  types.py                # CompletionResult, LLMRuntimeInfo, OllamaHealthSnapshot
```

## Related

- [Ollama Local LLM (RC2.7)](OLLAMA.md)
- [RAG Generation](RAG_GENERATION.md)
- [Configuration](CONFIGURATION.md)
- [FIRST_RUN](../FIRST_RUN.md)
