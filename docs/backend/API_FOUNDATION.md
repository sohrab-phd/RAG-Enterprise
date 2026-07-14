# API Foundation

> **Status:** Implemented infrastructure foundation.  
> **Authority:** Defines reusable HTTP contracts without business endpoints.

## Purpose

The API foundation standardizes HTTP responses, error translation, request tracing,
and OpenAPI metadata for all FastAPI routes.

Location: `backend/src/rag_enterprise/api/common/`

Business endpoints, authentication, and user management are intentionally not
implemented yet.

## Package structure

```text
api/common/
  responses.py      Success envelope models
  errors.py         Error envelope models and API exceptions
  pagination.py     Paginated response models
  handlers.py       Global exception handlers
  context.py        Request and correlation ID context
  middleware/       Request context and structured logging middleware
  versioning.py     API version helpers
  openapi.py        OpenAPI schema customization
```

## Response contract

Successful responses use a consistent envelope:

```json
{
  "success": true,
  "data": {}
}
```

Use `SuccessEnvelope[T]` or `success_response(data)` in route handlers. Paginated
collections use `PaginatedEnvelope[T]`:

```json
{
  "success": true,
  "data": {
    "items": [],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 0,
      "total_pages": 0,
      "has_next": false,
      "has_previous": false
    }
  }
}
```

## Error contract

Failed responses use a consistent envelope:

```json
{
  "success": false,
  "error": {
    "code": "not_found",
    "message": "Item not found",
    "details": {}
  }
}
```

| Source | Translation |
| --- | --- |
| `RequestValidationError` | `422` with `validation_failed` |
| `ApplicationException` | Status mapped from `ApplicationError.code` |
| `UnexpectedError` | `500` with `internal_error` |
| Uncaught `Exception` | `500` with safe generic message |

Application handlers should return `Result[T]` for expected failures. Routes map
`Result.fail(...)` to `ApplicationException` or use `from_application_error()` to
build envelopes directly.

## Middleware

| Middleware | Responsibility |
| --- | --- |
| `RequestContextMiddleware` | Assign/propagate `X-Request-ID` and `X-Correlation-ID` |
| `RequestLoggingMiddleware` | Emit structured `http_request_started` and `http_request_completed` logs |

Headers:

| Header | Behavior |
| --- | --- |
| `X-Request-ID` | Generated per request when absent; echoed on the response |
| `X-Correlation-ID` | Taken from the request when present; otherwise defaults to request ID |

Identifiers are bound to structlog context variables for downstream logging.

## Versioning

- Current version: `v1`
- Route prefix: `/api/v1`
- Helpers: `build_versioned_path()`, `get_api_version_from_path()`, `is_supported_api_version()`

New breaking API versions require a new router package (for example `api/v2/`) and an
ADR documenting migration behavior.

## OpenAPI conventions

`configure_openapi()` registers:

- application title and version from settings,
- tag descriptions for operational route groups,
- shared `ErrorDetail` and `ErrorEnvelope` schemas in components.

Route handlers should declare explicit `response_model` types and document error
responses with the shared error schemas where applicable.

## Dependency boundaries

```text
FastAPI route
  -> validate request DTO
  -> invoke application dispatcher/service
  -> map Result[T] to SuccessEnvelope or ApplicationException
```

Forbidden in routes:

- direct repository or ORM access,
- business rule evaluation,
- provider SDK calls.

## Testing strategy

API foundation tests live in `backend/tests/api/common/` and cover:

- success, error, and pagination envelopes,
- validation/application/unexpected exception translation,
- request and correlation ID propagation.

## Related documents

- [Application Layer](APPLICATION_LAYER.md)
- [Persistence Layer](PERSISTENCE_LAYER.md)
- [Configuration Validation (RC1.1)](CONFIGURATION.md)
- [Architecture Rules](../../.cursor/rules/architecture.md)
