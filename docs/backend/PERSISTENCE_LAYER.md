# Persistence Layer

> **Status:** Implemented infrastructure foundation.  
> **Authority:** Implements `docs/data/` and `docs/domain/` without redesigning the architecture.

## Purpose

The persistence layer provides reusable SQLAlchemy 2.x infrastructure for all future
RAG-enterprise modules. It contains no business entities.

Location: `backend/src/rag_enterprise/db/`

## Package structure

```text
db/
  base/           Declarative base and metadata naming conventions
  types/          UUIDv7 and shared DB types
  mixins/         Reusable ORM mixins
  session/        Engine, session factory, transactions, FastAPI dependency
  repositories/   Generic repository protocol and base implementation
  unit_of_work/   Async Unit of Work abstraction
```

## Identifier strategy

All future entities use **UUIDv7** primary keys generated in application code via
`rag_enterprise.db.types.generate_uuid7`.

This matches the approved data architecture:

- better PostgreSQL index locality than UUIDv4,
- distributed generation without sequences,
- native PostgreSQL `uuid` storage.

## Repository pattern

Repositories hide SQLAlchemy session details behind a narrow async interface.

### Contract

`RepositoryProtocol` defines:

- `get`
- `list`
- `add`
- `remove`
- `exists`

### Base implementation

`SQLAlchemyRepository` provides generic CRUD behavior for any `ModelBase` subclass.

Entity-specific repositories will:

1. subclass or compose `SQLAlchemyRepository`,
2. add domain-specific queries,
3. enforce tenant and ACL filters from the approved permission model.

### Soft delete behavior

If a model inherits `SoftDeleteMixin`, repository read paths exclude rows where
`deleted_at IS NOT NULL` unless `include_deleted=True`.

## Unit of Work

`SQLAlchemyUnitOfWork` defines the transaction boundary for application services.

### Responsibilities

- create or bind an `AsyncSession`,
- `commit()` successful work,
- `rollback()` failed work,
- close owned sessions on context exit.

### Usage pattern

```python
async with SQLAlchemyUnitOfWork(session_factory) as uow:
    repository = SQLAlchemyRepository(uow.session, FutureEntity)
    await repository.add(entity)
    await uow.commit()
```

Use Unit of Work for multi-repository application operations. Simple read-only paths
may use a request-scoped session dependency directly.

## Session lifecycle

### Application startup

`AppContainer.initialize()` creates:

1. async engine from `Settings.database`,
2. `async_sessionmaker` bound to that engine.

### Application shutdown

`AppContainer.shutdown()` disposes the engine and clears the session factory.

### Request-scoped dependency

`rag_enterprise.core.dependencies.database.get_db_session()` yields a session from the
container and wraps request work in `transaction(session)`:

- commit on success,
- rollback on exception.

This is appropriate for simple request handlers. Complex workflows should prefer
explicit Unit of Work usage in application services.

## Transaction boundaries

| Pattern | When to use |
| --- | --- |
| `transaction(session)` | Single request or script with one commit point |
| `SQLAlchemyUnitOfWork` | Application service coordinating multiple writes |
| read-only session | Queries with no commit |

Rules:

- one request must not share a session across tasks,
- repositories never commit; callers own transaction boundaries,
- long-running jobs open their own session per job partition.

## Mixins

Future entity models should compose approved mixins rather than redefining columns.

| Mixin | Purpose |
| --- | --- |
| `UUIDPrimaryKeyMixin` | UUIDv7 primary key |
| `TimestampMixin` | `created_at`, `updated_at` |
| `SoftDeleteMixin` | `deleted_at`, `deleted_by_user_id`, `delete_reason` |
| `OrganizationTenantMixin` | `organization_id` |
| `WorkspaceTenantMixin` | `organization_id`, `workspace_id` |
| `KnowledgeBaseTenantMixin` | workspace scope + `knowledge_base_id` |
| `ConversationTenantMixin` | workspace scope + `conversation_id` |
| `AuditMixin` | actor attribution |
| `VersionMixin` | optimistic concurrency via `row_version` |

Foreign keys to business entities will be added when entity models and migrations are
introduced.

## Configuration

Database settings live in:

- `rag_enterprise.core.config.database.DatabaseSettings`
- `rag_enterprise.core.config.settings.Settings`

Supported environment variables:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Primary async database URL |
| `DATABASE_TEST_URL` | Optional test database URL |
| `POSTGRES_HOST` | Host fallback when `DATABASE_URL` is absent |
| `POSTGRES_PORT` | Port fallback |
| `POSTGRES_USER` | User fallback |
| `POSTGRES_PASSWORD` | Password fallback |
| `POSTGRES_DB` | Database name fallback |
| `DATABASE_POOL_SIZE` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | Pool overflow |
| `DATABASE_POOL_TIMEOUT` | Pool checkout timeout |
| `DATABASE_POOL_RECYCLE` | Connection recycle interval |
| `DATABASE_ECHO` | SQL echo for debugging |

## Testing strategy

Persistence tests live in `backend/tests/db/` and use SQLite in-memory via `aiosqlite`.

Test-only models such as `tests.db.support.SampleRecord` validate the infrastructure
without introducing business entities.

## Next implementation steps

1. Add Alembic and first migration once entity models are defined.
2. Create entity-specific repositories with tenant and ACL filters.
3. Add pgvector column type and embedding repository specialization.
4. Add outbox table repository for domain events.

## Related documents

- [Data Architecture](../data/DATA_ARCHITECTURE.md)
- [Aggregates](../data/AGGREGATES.md)
- [Relationships](../data/RELATIONSHIPS.md)
- [Development Guide](../DEVELOPMENT.md)
