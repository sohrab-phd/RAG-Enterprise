# Knowledge Management — Validation Rules

> **Status:** Draft  
> **Applies to:** Application commands (not HTTP layer duplicates)

Each command lists validation rules, failure cases, authorization assumptions, idempotency,
and concurrency considerations. HTTP validation covers transport shape; this document covers
business validation returned as `ApplicationError` through the `Result` pattern.

## Authorization assumptions

Until authentication is implemented, commands assume:

| Assumption | Description |
| --- | --- |
| AUTH-01 | Trusted `user_id` and `organization_id` resolved from identity provider |
| AUTH-02 | Workspace membership is `active` for the actor |
| AUTH-03 | Permission checks use `docs/domain/PERMISSION_MODEL.md` |
| AUTH-04 | Resource ACL evaluated for `restricted+` classification |
| AUTH-05 | Tenant scope keys on every query: `organization_id`, `workspace_id` |

Denied authorization returns `forbidden` or `not_found` (no information leakage on hidden resources).

---

## Knowledge base commands

### CreateKnowledgeBase

| Category | Rule |
| --- | --- |
| Validation | `name` trimmed, 1–200 chars; `default_language` valid BCP-47; `visibility_policy` in allowed enum |
| Failure | Duplicate name → `conflict`; invalid workspace → `not_found`; workspace archived → `forbidden` |
| Authorization | `workspace:knowledge_base:create` |
| Idempotency | Same `X-Idempotency-Key` + payload returns original KB |
| Concurrency | N/A (insert only) |

### UpdateKnowledgeBase

| Category | Rule |
| --- | --- |
| Validation | At least one mutable field; name uniqueness if changed |
| Failure | KB `archived`/`deleted` → `conflict`; version mismatch → `conflict` |
| Authorization | `knowledge_base:manage` |
| Idempotency | Repeated identical PATCH is no-op success |
| Concurrency | `expected_version` optional optimistic lock |

### PublishKnowledgeBase

| Category | Rule |
| --- | --- |
| Validation | KB must be `draft` |
| Failure | Wrong status → `conflict` |
| Authorization | `knowledge_base:manage` |
| Idempotency | Publishing active KB returns current state |
| Concurrency | Single transition guarded by status check |

### ArchiveKnowledgeBase

| Category | Rule |
| --- | --- |
| Validation | KB must be `active` or `reindexing` |
| Failure | Already archived → idempotent success; deleted → `conflict` |
| Authorization | `knowledge_base:manage` |
| Idempotency | Repeat archive returns archived KB |
| Concurrency | Cascade update in one transaction; lock KB row |

### RestoreKnowledgeBase

| Category | Rule |
| --- | --- |
| Validation | KB `archived`; workspace `active` |
| Failure | KB `deleted` → `conflict` |
| Authorization | `knowledge_base:manage` |
| Idempotency | Repeat restore on active KB is no-op |
| Concurrency | Status transition atomic |

### DeleteKnowledgeBase

| Category | Rule |
| --- | --- |
| Validation | KB not already `deleted`; optional require `archived` first |
| Failure | Legal hold (future) → `conflict` |
| Authorization | `knowledge_base:manage` |
| Idempotency | Repeat delete returns success |
| Concurrency | Soft delete with `deleted_at` guard |

---

## Folder commands

### CreateFolder

| Category | Rule |
| --- | --- |
| Validation | Name unique among active siblings; depth ≤ max; parent in same KB |
| Failure | Parent archived → `conflict`; depth exceeded → `validation_failed` |
| Authorization | `folder:manage` |
| Idempotency | Idempotency key prevents duplicate folder on retry |
| Concurrency | Sibling name check within transaction (serializable or unique index) |

### RenameFolder

| Category | Rule |
| --- | --- |
| Validation | New name unique among siblings |
| Failure | Folder archived → `conflict` |
| Authorization | `folder:manage` |
| Idempotency | Same name no-op |
| Concurrency | `expected_version` on folder row |

### MoveFolder

| Category | Rule |
| --- | --- |
| Validation | No cycle; target depth + subtree depth ≤ max; unique name at target |
| Failure | Move into self/descendant → `validation_failed`; target archived → `conflict` |
| Authorization | `folder:manage` |
| Idempotency | Move to same parent is no-op |
| Concurrency | Lock subtree root; batch path update |

### ArchiveFolder

| Category | Rule |
| --- | --- |
| Validation | Folder `active`; `cascade` flag honored |
| Failure | Already archived → idempotent success |
| Authorization | `folder:manage` |
| Idempotency | Repeat archive safe |
| Concurrency | Subtree batch update in one transaction |

### RestoreFolder

| Category | Rule |
| --- | --- |
| Validation | Folder `archived`; ancestors `active` |
| Failure | Parent archived → `conflict` ("restore parent first") |
| Authorization | `folder:manage` |
| Idempotency | Repeat restore safe |
| Concurrency | Status check on parent chain |

### DeleteFolder

| Category | Rule |
| --- | --- |
| Validation | No active children unless `force` cascade approved |
| Failure | Non-empty without force → `conflict` |
| Authorization | `folder:manage` |
| Idempotency | Repeat delete safe |
| Concurrency | Child count check in transaction |

---

## Document commands

### CreateDocument

| Category | Rule |
| --- | --- |
| Validation | Title 1–500 chars; folder in KB; tags ≤ 50; metadata ≤ 16 KB JSON |
| Failure | KB archived → `forbidden`; folder archived → `conflict` |
| Authorization | `document:create` |
| Idempotency | Idempotency key returns same document |
| Concurrency | N/A |

### UpdateDocumentMetadata

| Category | Rule |
| --- | --- |
| Validation | Same bounds as create; classification change may require `knowledge_base:manage` |
| Failure | Document archived/deleted → `conflict` |
| Authorization | `document:update`; ACL `edit` for restricted docs |
| Idempotency | Identical update no-op |
| Concurrency | `expected_version` on document |

### MoveDocument

| Category | Rule |
| --- | --- |
| Validation | Target folder same KB, `active` |
| Failure | Document archived → `conflict` |
| Authorization | `document:update` |
| Idempotency | Move to current folder no-op |
| Concurrency | Row lock on document |

### ArchiveDocument

| Category | Rule |
| --- | --- |
| Validation | Document `active` or `draft` |
| Failure | Already archived → idempotent success |
| Authorization | `document:update` or `document:delete` per policy |
| Idempotency | Safe to repeat |
| Concurrency | Status transition atomic |

### RestoreDocument

| Category | Rule |
| --- | --- |
| Validation | Document `archived`; folder/KB not deleted |
| Failure | Parent folder archived → `conflict` |
| Authorization | `document:update` |
| Idempotency | Safe to repeat |
| Concurrency | Status transition atomic |

### DeleteDocument

| Category | Rule |
| --- | --- |
| Validation | `legal_hold` must be false |
| Failure | Already deleted → idempotent; legal hold → `conflict` |
| Authorization | `document:delete` |
| Idempotency | Safe to repeat |
| Concurrency | Soft delete guard on `deleted_at` |

---

## Document version commands

### CreateDocumentVersion

| Category | Rule |
| --- | --- |
| Validation | Upload `completed`, unbound; file format allowed; hash verified |
| Failure | Upload expired → `conflict`; bound upload → `conflict`; doc archived → `conflict` |
| Authorization | `document:update` |
| Idempotency | Same `upload_id` returns same version |
| Concurrency | `version_number` assigned with document-level lock |

### SetCurrentVersion (internal)

| Category | Rule |
| --- | --- |
| Validation | Target version `indexed` or policy allows pre-index pointer |
| Failure | Version not belonging to document → `validation_failed` |
| Authorization | System or `document:update` |
| Idempotency | Same pointer no-op |
| Concurrency | Update `current_version_id` atomically |

---

## Upload commands

### InitiateUpload

| Category | Rule |
| --- | --- |
| Validation | `file_size_bytes` > 0 and ≤ max; extension/MIME in allowlist; KB ingestible |
| Failure | Quota exceeded → `conflict`; workspace archived → `forbidden` |
| Authorization | `document:create` or `document:update` |
| Idempotency | Optional key returns same session if pending |
| Concurrency | Per-user rate limit (Redis) |

### CompleteUpload

| Category | Rule |
| --- | --- |
| Validation | Session `pending`/`uploading`; object exists; size matches; hash if provided |
| Failure | Expired → `conflict`; size mismatch → `validation_failed` |
| Authorization | Session owner or same permissions as initiate |
| Idempotency | Repeat complete returns completed session |
| Concurrency | Transition status with row lock |

### CancelUpload

| Category | Rule |
| --- | --- |
| Validation | Session not `completed` |
| Failure | Already completed → `conflict` |
| Authorization | Session owner |
| Idempotency | Repeat cancel safe |
| Concurrency | Status guard |

### InitiateBulkUpload

| Category | Rule |
| --- | --- |
| Validation | `files.length` 1–100; each file within size limit; total batch size within org quota |
| Failure | Too many files → `validation_failed` |
| Authorization | `document:create` |
| Idempotency | Batch key returns same batch |
| Concurrency | N/A |

### CompleteBulkUpload

| Category | Rule |
| --- | --- |
| Validation | Each `upload_id` belongs to batch; batch `open` |
| Failure | Batch expired → `conflict`; unknown upload → `validation_failed` |
| Authorization | `document:create` |
| Idempotency | Per-item create uses upload binding idempotency |
| Concurrency | Per-file partial success; no whole-batch rollback |

---

## Metadata commands

### ReplaceDocumentMetadata

| Category | Rule |
| --- | --- |
| Validation | Full replacement object; keys alphanumeric; no PII in keys per policy |
| Failure | Document not mutable → `conflict` |
| Authorization | `document:update` |
| Idempotency | Same payload no-op |
| Concurrency | `expected_version` |

---

## Cross-cutting validation

### Tenant scope

Every command validates that:

- `workspace_id` belongs to `organization_id`
- `knowledge_base_id` belongs to `workspace_id`
- `folder_id` and `document_id` belong to `knowledge_base_id`

Mismatch returns `not_found` (never `forbidden` with cross-tenant ID).

### Status gates

| Operation | Blocked statuses |
| --- | --- |
| Upload | KB `archived`, `deleted`; workspace `archived` |
| Metadata update | Document `archived`, `deleted` |
| Move | Document/folder `archived`, `deleted` |
| Restore | Document/KB not in restorable state |

### File format validation

| Format | Detection | v1 support |
| --- | --- | --- |
| PDF | Magic bytes + MIME | Yes (native text) |
| DOCX | ZIP structure | Yes |
| TXT, MD | Extension + MIME | Yes |
| HTML | MIME | Yes |
| Images | MIME | No (future OCR) |
| ZIP, EXE | — | Rejected |

### Duplicate names

| Scope | Rule |
| --- | --- |
| KB name | Unique per workspace among non-deleted |
| Folder name | Unique per parent among active |
| Document title | Warning only in v1 unless `enforce_unique_titles` policy enabled |

### Content hash duplicates

| Scenario | v1 behavior |
| --- | --- |
| Same hash, same document | Warn; allow new version if user confirms |
| Same hash, different document | Allow; optional dedup hint in response |

---

## Concurrency summary

| Hot spot | Strategy |
| --- | --- |
| Folder sibling rename | Unique composite index + transaction |
| Version number allocation | `SELECT MAX ... FOR UPDATE` on document |
| Folder subtree move | Lock root; single transaction path recompute |
| KB archive cascade | Batch updates with KB row lock |
| Upload complete | Optimistic status transition `pending` → `completed` |
| Optimistic entity version | Client `expected_version` → `409 conflict` |

---

## Related documents

- [API.md](API.md)
- [WORKFLOWS.md](WORKFLOWS.md)
- [ACCEPTANCE.md](ACCEPTANCE.md)
- [../../docs/domain/PERMISSION_MODEL.md](../../docs/domain/PERMISSION_MODEL.md)
