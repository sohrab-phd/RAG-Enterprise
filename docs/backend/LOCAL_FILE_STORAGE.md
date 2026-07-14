# Local File Storage (RC1.6)

> **Status:** Implemented  
> **Scope:** Durable local filesystem storage for upload binaries. No S3/MinIO/plugins.

## Purpose

Store document upload payloads on disk under a configurable root so restarts and
multi-request demos keep content. Unit tests continue to use
`InMemoryFileStorage`.

## Layout

`FILE_STORAGE_ROOT` defaults to `storage/uploads`:

```text
{FILE_STORAGE_ROOT}/
  {organization_id}/
    {workspace_id}/
      {document_id}/
        {document_version_id}/
          {file_name}
      staging/
        {upload_id}
```

Directories are created automatically on write.

## Configuration

| Env | Default | Notes |
| --- | --- | --- |
| `FILE_STORAGE_ROOT` | `storage/uploads` | Created and checked writable at startup |

Startup validation (RC1.1) creates the directory when missing. Readiness (RC1.2)
probes `put` → `get` → `delete` through the `FileStorage` interface.

## Runtime wiring

| Context | Implementation |
| --- | --- |
| `AppContainer.initialize` (normal runtime) | `FileSystemStorage` |
| Unit/component tests | `InMemoryFileStorage` (explicit fixture override) |

Upload HTTP handlers are unchanged: they call `FileStorage.put` / `get` with
opaque keys produced by `storage_key_for_version` / `staging_storage_key`.

## Package

```text
knowledge/infrastructure/
  filesystem.py   # FileSystemStorage
  storage.py      # InMemoryFileStorage + key helpers
```

## Testing

```bash
cd backend
uv run pytest tests/knowledge/test_filesystem_storage.py tests/knowledge/test_api.py -q
```

## Related documents

- [Operational Health](OPERATIONAL_HEALTH.md)
- [Configuration Validation](CONFIGURATION.md)
- [Knowledge Management](KNOWLEDGE_MANAGEMENT.md)
- [Documentation index](../README.md)
