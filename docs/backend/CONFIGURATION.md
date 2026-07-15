# Configuration Validation (RC1.1)

> **Status:** Implemented  
> **Scope:** Startup configuration checks only — no Settings redesign, API, or business-logic changes.

## Purpose

Validate application configuration **during startup** and fail fast before the
process accepts traffic. Operators get a single console report with issues
grouped by subsystem.

## When validation runs

`rag_enterprise.lifespan.lifespan` calls `validate_configuration(settings)`
before logging setup completes container initialization and before any request
is served.

On failure:

1. A human-readable report is written to **stderr**.
2. The process exits with status `1` (`SystemExit`).

## Package

```text
backend/src/rag_enterprise/core/config/
  settings.py       # Settings + DatabaseSettings assembly (unchanged design)
  database.py       # DatabaseSettings
  validation.py     # RC1.1 validator, report formatter, ConfigurationError
```

## Groups and checks

| Group | Rules |
| --- | --- |
| **Database** | Non-empty host/user/name; port 1–65535; pool size & timeouts positive; max overflow ≥ 0; resolved URL uses postgresql/sqlite |
| **LLM** | `LLM_BACKEND` ∈ `{local, api, mock}` (legacy `echo`→`mock`, `http`→`api`); provider enums; model key non-empty after normalize (`auto` or explicit; empty→`auto`); positive timeout; evidence score in `[0, 1]`. **`mock` does not require credentials.** **`api` requires `OPENAI_API_KEY` and `OPENAI_BASE_URL`** (or legacy `LLM_API_KEY` / `LLM_BASE_URL`). **`local` requires `OLLAMA_BASE_URL`.** See [OLLAMA.md](OLLAMA.md). |
| **Embedding** | `EMBEDDING_BACKEND` ∈ `{sentence_transformers, deterministic, flag}`; non-empty model key; dimensions, batch size, and default top_k positive. **Production / RC2.3–RC2.5:** `sentence_transformers` + `BAAI/bge-m3` + `1024`. `deterministic` is for explicit CI/test use only. |
| **Evaluation** | `EVALUATION_STORAGE_ROOT` non-empty; create directory if missing; path must be a directory |
| **Upload** | `FILE_STORAGE_ROOT` non-empty; create/writable directory; `UPLOAD_MAX_FILE_SIZE_BYTES`, `UPLOAD_MAX_BULK_FILES`, `UPLOAD_SESSION_TTL_HOURS` must be positive |
| **Logging** | `LOG_LEVEL` ∈ `{CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET}` |
| **Environment** | `APP_ENV` ∈ `{development, staging, production, test}`; backend port in range; API prefix starts with `/` |

Invalid enum-like values are rejected by the startup validator (`LLM_BACKEND`,
`EMBEDDING_BACKEND`, `APP_ENV`, `LOG_LEVEL`). Pydantic `Literal` fields on
`Settings` also constrain construction when values are supplied without a
conflicting environment override.

## Example console report

```text
Configuration validation failed. Fix the issues below and restart.

[LLM]
  - OPENAI_API_KEY: OPENAI_API_KEY (or legacy LLM_API_KEY) is required when LLM_BACKEND=api
  - OPENAI_BASE_URL: OPENAI_BASE_URL (or legacy LLM_BASE_URL) is required when LLM_BACKEND=api

[Upload]
  - UPLOAD_MAX_FILE_SIZE_BYTES: max file size must be positive (got 0)

Total issues: 3
```

## Upload settings

These env vars are validated at startup (defaults match knowledge constants).
Request handlers still use `knowledge.constants` for enforcement in RC1.1 — the
settings fields exist so operators can fail fast on bad deploy config.

| Env | Default |
| --- | --- |
| `FILE_STORAGE_ROOT` | `storage/uploads` |
| `UPLOAD_MAX_FILE_SIZE_BYTES` | `52428800` (50 MiB) |
| `UPLOAD_MAX_BULK_FILES` | `100` |
| `UPLOAD_SESSION_TTL_HOURS` | `24` |

Local binary layout: [Local File Storage (RC1.6)](LOCAL_FILE_STORAGE.md).

## Testing

```bash
cd backend
uv run pytest tests/core/test_config_validation.py -q
```

## Related documents

- [Operational Health (RC1.2)](OPERATIONAL_HEALTH.md) — readiness uses the config-validated flag
- [Local File Storage (RC1.6)](LOCAL_FILE_STORAGE.md) — `FILE_STORAGE_ROOT`
- [Persistence Layer](PERSISTENCE_LAYER.md) — database settings
- [RAG Generation](RAG_GENERATION.md) — LLM settings
- [Embeddings & Retrieval](EMBEDDINGS_AND_RETRIEVAL.md) — embedding backends
- [Evaluation Framework](EVALUATION_FRAMEWORK.md) — artifact storage root
