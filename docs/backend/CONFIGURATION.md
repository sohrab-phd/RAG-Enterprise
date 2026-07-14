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
| **LLM** | `LLM_BACKEND` ∈ `{echo, http}`; non-empty model key; positive timeout; evidence score in `[0, 1]`. **`echo` does not require an API key.** **`http` requires `LLM_API_KEY` and `LLM_BASE_URL`.** |
| **Embedding** | `EMBEDDING_BACKEND` ∈ `{deterministic, flag}`; non-empty model key; dimensions, batch size, and default top_k positive |
| **Evaluation** | `EVALUATION_STORAGE_ROOT` non-empty; create directory if missing; path must be a directory |
| **Upload** | `UPLOAD_MAX_FILE_SIZE_BYTES`, `UPLOAD_MAX_BULK_FILES`, `UPLOAD_SESSION_TTL_HOURS` must be positive |
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
  - LLM_API_KEY: API key is required when LLM_BACKEND=http
  - LLM_BASE_URL: base URL is required when LLM_BACKEND=http

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
| `UPLOAD_MAX_FILE_SIZE_BYTES` | `52428800` (50 MiB) |
| `UPLOAD_MAX_BULK_FILES` | `100` |
| `UPLOAD_SESSION_TTL_HOURS` | `24` |

## Testing

```bash
cd backend
uv run pytest tests/core/test_config_validation.py -q
```

## Related documents

- [Persistence Layer](PERSISTENCE_LAYER.md) — database settings
- [RAG Generation](RAG_GENERATION.md) — LLM settings
- [Embeddings & Retrieval](EMBEDDINGS_AND_RETRIEVAL.md) — embedding backends
- [Evaluation Framework](EVALUATION_FRAMEWORK.md) — artifact storage root
