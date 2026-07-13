# ADR-003: Database Selection

**Status:** Accepted  
**Date:** 2026-07-13

## Context

The platform requires durable relational data with transactions, constraints,
tenant-aware access, metadata filtering, and eventually vector similarity search.
Operational simplicity, data integrity, backup maturity, and the ability to combine
relational filters with vector retrieval are more important than optimizing a
single early workload. Redis is also planned for ephemeral caching or coordination,
but it is not a system of record.

## Decision

Use PostgreSQL as the authoritative transactional datastore and pgvector as its
initial vector extension. Use SQLAlchemy 2 async adapters behind domain-owned
repository interfaces when persistence is implemented.

- PostgreSQL constraints enforce critical data invariants.
- All tenant-owned access is scoped by trusted tenant identity.
- Schema changes use reviewed, reversible migrations with mixed-version deployment
  and backfill plans.
- Embeddings retain model/version, dimensions, source lineage, ACL metadata, and
  indexing state.
- Vector distance metric and index type are selected and measured per approved RAG
  specification rather than assumed in this ADR.
- Redis remains an optional ephemeral dependency; correctness must not depend on
  cache persistence.

## Alternatives considered

### Dedicated vector database

May provide specialized scale and retrieval features, but adds another operational
system, consistency boundary, authorization path, and synchronization process before
requirements demonstrate PostgreSQL/pgvector is insufficient.

### Document database

Offers flexible documents but weakens relational constraints and transactional joins
needed for enterprise metadata, tenancy, lifecycle, and audit requirements.

### Managed search engine

Could support hybrid and full-text search at scale, but introduces additional
operations and synchronization. It may be reconsidered when measured retrieval
requirements justify it.

## Consequences

- Relational metadata and vector filtering can share transactions and authorization
  constraints.
- The initial operational footprint remains small and locally reproducible.
- Large-scale vector workloads may eventually require partitioning, replicas, or a
  dedicated retrieval system; migration must preserve lineage and ACLs.
- Embedding/index changes require explicit re-indexing, rollout, and rollback plans.
- PostgreSQL capacity, vacuum, indexes, connection pools, backups, and restore
  procedures become production-critical responsibilities.
