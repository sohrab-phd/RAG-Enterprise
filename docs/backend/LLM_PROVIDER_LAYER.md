# LLM Provider Layer (RC2.6)

> **Status:** Implemented  
> **Scope:** Provider subsystem only — GenerationService, PromptBuilder, Retrieval, and
> chat APIs are unchanged. Ollama **generate** lands in RC2.7.

## Architecture

```text
GenerationService
       │  depends only on LLMProvider (protocol)
       ▼
 create_llm_provider(settings)   ← sole construction site
       │
       ├── LLM_BACKEND=local  → LocalProvider / OllamaProvider (structure; no generate yet)
       ├── LLM_BACKEND=api    → APIProvider / OpenAICompatibleProvider
       └── LLM_BACKEND=mock   → MockProvider (legacy echo behavior)
```

| Backend | Provider (V1) | Purpose |
|---------|---------------|---------|
| **local** (default) | `ollama` | On-machine execution via Ollama (wired for config; generate = RC2.7) |
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
| `LLM_MODEL_KEY` | `auto` | Use `gpt-4o-mini` (or other) for `api` |
| `LLM_TIMEOUT_SECONDS` | `60` | Shared timeout |

### Backward compatibility

| Legacy | Maps to | Warning |
|--------|---------|---------|
| `LLM_BACKEND=echo` | `mock` | `echo/http are deprecated; use local/api/mock.` |
| `LLM_BACKEND=http` | `api` | same |
| `LLM_BASE_URL` / `LLM_API_KEY` | fill `OPENAI_*` when unset | Prefer `OPENAI_*` |

## Health / system

`GET /api/v1/system` includes:

```json
"llm": {
  "backend": "local",
  "provider": "ollama",
  "model": "auto",
  "timeout_seconds": 60.0
}
```

`providers.llm` also reports `reachability: "not_checked"` and `latency_ms: null`
(no Ollama probe until RC2.7).

## Package layout

```text
generation/providers/
  factory.py              # create_llm_provider / describe_llm_runtime
  local.py / api.py       # category bases
  ollama.py               # LocalProvider implementation (stub complete)
  openai_compatible.py    # API OpenAI-compatible client
  mock.py                 # echo MockProvider
  types.py                # CompletionResult, LLMRuntimeInfo
```

## Related

- [RAG Generation](RAG_GENERATION.md)
- [Configuration](CONFIGURATION.md)
- [FIRST_RUN](../FIRST_RUN.md)
