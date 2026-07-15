# Operational Health (RC1.2)

> **Status:** Implemented  
> **Scope:** Liveness, readiness, and system inventory probes — no auth, no frontend.
> Readiness does not call embedding providers. When `LLM_BACKEND=local`, readiness
> probes Ollama through the LLM provider (see [OLLAMA.md](OLLAMA.md)).

## Endpoints

All routes are unauthenticated and live under `/api/v1`.

| Path | Purpose | Dependencies |
| --- | --- | --- |
| `GET /live` | Process liveness | None (immediate) |
| `GET /ready` | Traffic readiness | DI, config flag, DB `SELECT 1`, evaluation dir, upload storage probe; **`llm` when `LLM_BACKEND=local`** |
| `GET /system` | Operator inventory | Settings + optional DB/eval counts (+ LLM inventory) |
| `GET /system/models` | LLM model catalog | Settings + provider inventory |
| `GET /health` | Legacy compatibility | Settings only |

### `/live`

Always `200`:

```json
{ "status": "live", "timestamp": "…" }
```

### `/ready`

`200` when every check passes; `503` when any fail.

Checks (bounded to ~2s each):

| Check | Pass criteria |
| --- | --- |
| `configuration` | RC1.1 validation marked complete in lifespan |
| `dependency_injection` | `AppContainer.is_initialized` |
| `database` | `SELECT 1` via SQLAlchemy engine |
| `evaluation_storage` | `EVALUATION_STORAGE_ROOT` is a writable directory |
| `upload_storage` | local filesystem `put` → `get` → `delete` probe ([LOCAL_FILE_STORAGE.md](LOCAL_FILE_STORAGE.md)) |
| `llm` | Only when `LLM_BACKEND=local`: Ollama reachable, models, selected model, generation ping ([OLLAMA.md](OLLAMA.md)) |

Does **not** call embedding providers. Local LLM probes run only for `LLM_BACKEND=local`.

### `/system`

Returns configured inventory (never invokes models):

- `version`, `environment`
- provider names + modes (`llm`: `local|api|mock` with provider `ollama|openai|echo`; embeddings:
  `deterministic|flag|sentence_transformers`)
- dedicated `llm` object: `backend`, `provider`, `model`, `selected_model`,
  `installed_models`, `timeout_seconds`, `ollama_version`, `selection_mode`, `reachability`
- `GET /system/models` developer catalog for installed / selected models
- reachability on `providers.llm` reflects the local provider after init when available
- configured model keys + embedding dimensions + prompt template version `v1`
- counts: documents, chunks, embeddings, evaluation runs
- `configuration_validated`, `dependency_injection_initialized`

`503` when DI is not initialized (counts may be zero / `ok: false`).

## Implementation

```text
rag_enterprise.core.runtime      # configuration_validated flag
rag_enterprise.core.health       # readiness + system inventory helpers
rag_enterprise.api.v1.endpoints.health
rag_enterprise.lifespan          # marks config validated after RC1.1
```

## Testing

```bash
cd backend
uv run pytest tests/api/v1/test_health.py -q
```

## Related documents

- [Configuration Validation (RC1.1)](CONFIGURATION.md)
- [Local File Storage (RC1.6)](LOCAL_FILE_STORAGE.md)
- [End-to-End Happy Path (RC1.3)](E2E_HAPPY_PATH.md)
- [API Foundation](API_FOUNDATION.md)
- [Architecture](../ARCHITECTURE.md)
