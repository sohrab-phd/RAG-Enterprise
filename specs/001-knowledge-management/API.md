# Knowledge Management — API Contract

> **Status:** Draft — design only, no implementation  
> **Base path:** `/api/v1`  
> **Response envelope:** Platform standard (`success`, `data` / `error`)

## Conventions

### Scoping

All knowledge resources are workspace-scoped unless noted.

```text
/api/v1/workspaces/{workspace_id}/...
```

Path parameters:

| Parameter | Type | Description |
| --- | --- | --- |
| `workspace_id` | UUID | Workspace scope for authorization and tenancy |
| `knowledge_base_id` | UUID | Knowledge base identifier |
| `folder_id` | UUID | Folder identifier |
| `document_id` | UUID | Document identifier |
| `version_id` | UUID | Document version identifier |
| `upload_id` | UUID | Upload session identifier |

### Headers

| Header | Required | Description |
| --- | --- | --- |
| `Authorization` | Yes (when auth enabled) | Bearer token |
| `X-Correlation-ID` | No | Propagated by platform middleware |
| `X-Idempotency-Key` | Conditional | Required on mutating commands marked idempotent |
| `Content-Type` | Conditional | `application/json` or `multipart/form-data` for uploads |

### Common query parameters

| Parameter | Applies to | Description |
| --- | --- | --- |
| `page` | List endpoints | Page number (default 1) |
| `page_size` | List endpoints | Items per page (default 20, max 100) |
| `status` | Lists | Filter by lifecycle status |
| `q` | Lists | Case-insensitive name/title search |
| `include_deleted` | Admin lists | Include soft-deleted rows (requires elevated permission) |

### Standard error codes

| Code | HTTP | When |
| --- | --- | --- |
| `validation_failed` | 422 | Request validation failure |
| `unauthorized` | 401 | Missing or invalid identity |
| `forbidden` | 403 | Permission denied |
| `not_found` | 404 | Resource not found or not visible |
| `conflict` | 409 | Name conflict, state conflict, version conflict |
| `internal_error` | 500 | Unexpected failure |

---

## Knowledge bases

### List knowledge bases

`GET /workspaces/{workspace_id}/knowledge-bases`

**Permission:** `knowledge_base:read`

**Response `data`:** Paginated list of knowledge base summaries.

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Knowledge base ID |
| `name` | string | Display name |
| `status` | enum | `draft`, `active`, `reindexing`, `archived`, `deleted` |
| `default_language` | string | BCP-47 locale |
| `visibility_policy` | enum | `private`, `workspace`, `organization` |
| `document_count` | int | Active documents |
| `created_at` | datetime | UTC |
| `updated_at` | datetime | UTC |

---

### Create knowledge base

`POST /workspaces/{workspace_id}/knowledge-bases`

**Permission:** `workspace:knowledge_base:create`

**Request body:**

| Field | Required | Description |
| --- | --- | --- |
| `name` | Yes | 1–200 characters, unique per workspace among active KBs |
| `default_language` | No | BCP-47; default `en` |
| `visibility_policy` | No | Default `workspace` |
| `description` | No | Optional summary, max 2000 chars |

**Response:** `201 Created` with knowledge base detail.

**Idempotency:** `X-Idempotency-Key` deduplicates create within 24 hours.

---

### Get knowledge base

`GET /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}`

**Permission:** `knowledge_base:read`

---

### Update knowledge base

`PATCH /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}`

**Permission:** `knowledge_base:manage`

**Mutable fields:** `name`, `default_language`, `visibility_policy`, `description`

**Blocked when:** `archived`, `deleted`, or workspace archived.

---

### Publish knowledge base

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/publish`

**Permission:** `knowledge_base:manage`

**Precondition:** KB in `draft` (publishing an already `active` KB is idempotent).

**Effect:** KB → `active`. Empty knowledge bases are allowed.

**Response:** Updated knowledge base detail.

---

### Archive knowledge base

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/archive`

**Permission:** `knowledge_base:manage`

**Effect:** KB → `archived`; cascades archive to folders and documents.

**Response:** Updated knowledge base detail.

---

### Restore knowledge base

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/restore`

**Permission:** `knowledge_base:manage`

**Precondition:** KB status is `archived`; workspace is `active`.

**Effect:** KB → `active` (folders/documents remain archived until individually restored or bulk restore policy applies — see WORKFLOWS.md).

---

### Delete knowledge base

`DELETE /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}`

**Permission:** `knowledge_base:manage`

**Effect:** Soft delete → `deleted` after archive precondition or direct soft delete per policy.

**Response:** `204 No Content` or deleted resource summary.

---

## Folders

### List folders

`GET /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/folders`

**Permission:** `folder:read`

**Query:** `parent_folder_id` (omit for root children), `status`, `page`, `page_size`

---

### Create folder

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/folders`

**Permission:** `folder:manage`

**Request body:**

| Field | Required | Description |
| --- | --- | --- |
| `name` | Yes | Unique among active siblings |
| `parent_folder_id` | No | Null for KB root level |

---

### Get folder

`GET /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/folders/{folder_id}`

**Permission:** `folder:read`

**Response includes:** `path`, `depth`, `parent_folder_id`, `status`, child counts.

---

### Update folder (rename)

`PATCH /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/folders/{folder_id}`

**Permission:** `folder:manage`

**Mutable fields:** `name`

---

### Move folder

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/folders/{folder_id}/move`

**Permission:** `folder:manage`

**Request body:**

| Field | Required | Description |
| --- | --- | --- |
| `target_parent_folder_id` | No | Null to move to KB root |
| `expected_version` | No | Optimistic concurrency token |

**Failure:** `409 conflict` if move would create cycle or duplicate name.

---

### Archive folder

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/folders/{folder_id}/archive`

**Permission:** `folder:manage`

**Query:** `cascade=true` (default) archives subtree.

---

### Restore folder

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/folders/{folder_id}/restore`

**Permission:** `folder:manage`

**Precondition:** Parent folder and knowledge base are not archived/deleted.

---

### Delete folder

`DELETE /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/folders/{folder_id}`

**Permission:** `folder:manage`

**Precondition:** Empty folder or `force=false` blocked when children exist.

---

## Documents

### List documents

`GET /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/documents`

**Permission:** `document:read`

**Query:** `folder_id`, `status`, `declared_language`, `q`, `page`, `page_size`

---

### Create document (metadata only)

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/documents`

**Permission:** `document:create`

**Request body:**

| Field | Required | Description |
| --- | --- | --- |
| `title` | Yes | 1–500 characters |
| `folder_id` | No | Target folder; default root |
| `declared_language` | No | BCP-47; default KB `default_language` |
| `source_type` | No | Default `upload` |
| `classification_label` | No | Default `public_internal` |
| `tags` | No | String array, max 50 tags |
| `metadata` | No | JSON object, max 16 KB serialized |

**Response:** `201` document in `draft` status without file content.

---

### Get document

`GET /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/documents/{document_id}`

**Permission:** `document:read`

**Response includes:** current version summary, status, folder placement, ACL summary (if permitted).

---

### Update document metadata

`PATCH /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/documents/{document_id}`

**Permission:** `document:update`

**Mutable fields:** `title`, `declared_language`, `classification_label`, `tags`, `metadata`

**Blocked when:** document `archived` or `deleted`.

---

### Move document

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/documents/{document_id}/move`

**Permission:** `document:update`

**Request body:**

| Field | Required | Description |
| --- | --- | --- |
| `target_folder_id` | No | Null for KB root |

---

### Archive document

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/documents/{document_id}/archive`

**Permission:** `document:delete` or `document:update` per tenant policy (default: `document:update`)

**Effect:** Document → `archived`; excluded from active retrieval.

---

### Restore document

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/documents/{document_id}/restore`

**Permission:** `document:update`

**Precondition:** Document `archived`; parent folder and KB not deleted.

---

### Delete document

`DELETE /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/documents/{document_id}`

**Permission:** `document:delete`

**Effect:** Soft delete → `deleted`; versions retained.

---

## Document versions

### List versions

`GET /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/documents/{document_id}/versions`

**Permission:** `document:read`

**Response:** Paginated version summaries ordered by `version_number` descending.

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Version ID |
| `version_number` | int | Monotonic per document |
| `extraction_method` | enum | `native_text`, future: `ocr`, `connector_import` |
| `processing_status` | enum | See ENTITY_LIFECYCLE |
| `content_hash` | string | SHA-256 hex |
| `file_name` | string | Original filename |
| `file_size_bytes` | int | Size |
| `mime_type` | string | Detected MIME |
| `is_current` | bool | Current version pointer |
| `created_at` | datetime | UTC |

---

### Get version

`GET /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/documents/{document_id}/versions/{version_id}`

**Permission:** `document:read`

---

### Create new version (from completed upload)

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/documents/{document_id}/versions`

**Permission:** `document:update`

**Request body:**

| Field | Required | Description |
| --- | --- | --- |
| `upload_id` | Yes | Completed upload session |
| `change_summary` | No | Human-readable note, max 500 chars |

**Response:** `201` new version in `uploaded` state.

**Idempotency:** Same `upload_id` cannot bind to two versions.

---

### Get version processing status

`GET /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/documents/{document_id}/versions/{version_id}/status`

**Permission:** `document:read`

**Response:**

| Field | Description |
| --- | --- |
| `processing_status` | Current pipeline state |
| `failure_reason` | Present when `failed` |
| `retryable` | Whether client may retry |
| `indexed_at` | Present when `indexed` |

---

### Download version original file

`GET /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/documents/{document_id}/versions/{version_id}/download`

**Permission:** `document:download`

**Response:** `302` to short-lived signed URL or streamed binary with `Content-Disposition`.

---

## Metadata

### Get document metadata

`GET /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/documents/{document_id}/metadata`

**Permission:** `document:read`

**Response:** Tags, custom metadata, classification, language, source provenance.

---

### Replace document metadata

`PUT /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/documents/{document_id}/metadata`

**Permission:** `document:update`

**Request body:** Full metadata object (replaces tags and custom `metadata` keys).

---

## Uploads

### Initiate upload session

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/uploads`

**Permission:** `document:create` or `document:update`

**Request body:**

| Field | Required | Description |
| --- | --- | --- |
| `file_name` | Yes | Original filename |
| `file_size_bytes` | Yes | Declared size for quota check |
| `mime_type` | No | Client hint |
| `document_id` | No | If set, upload is for new version; else paired at document create |
| `checksum_sha256` | No | Pre-computed hash for integrity verification |

**Response `data`:**

| Field | Description |
| --- | --- |
| `upload_id` | Session identifier |
| `upload_url` | Single PUT URL or multipart upload instructions |
| `expires_at` | Session expiry |
| `max_part_size_bytes` | For multipart |

---

### Upload binary (single-shot)

`PUT /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/uploads/{upload_id}/content`

**Permission:** Same as initiate

**Request:** Raw binary body

**Response:** `204 No Content` on success

---

### Complete upload

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/uploads/{upload_id}/complete`

**Permission:** Same as initiate

**Request body (optional):**

| Field | Description |
| --- | --- |
| `checksum_sha256` | Verified server-side against stored object |

**Response:** Upload session with `status = completed`.

---

### Cancel upload

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/uploads/{upload_id}/cancel`

**Permission:** Same as initiate

**Effect:** Marks session cancelled; staged object deleted.

---

### Bulk upload

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/uploads/bulk`

**Permission:** `document:create`

**Request body:**

| Field | Required | Description |
| --- | --- | --- |
| `folder_id` | No | Target folder for all new documents |
| `files` | Yes | Array of `{ file_name, file_size_bytes, mime_type? }`, max 100 |
| `default_metadata` | No | Applied to each created document |

**Response `data`:**

| Field | Description |
| --- | --- |
| `batch_id` | Bulk operation identifier |
| `uploads` | Array of per-file upload session descriptors |
| `expires_at` | Batch expiry |

**Follow-up:** Client completes each upload, then calls bulk complete.

---

### Complete bulk upload

`POST /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/uploads/bulk/{batch_id}/complete`

**Permission:** `document:create`

**Request body:**

| Field | Description |
| --- | --- |
| `items` | `{ upload_id, title?, tags? }` per completed upload |

**Response:** Summary with per-file `succeeded` / `failed` results.

---

## Status changes

Dedicated endpoints above cover publish, archive, restore, and delete.

---

## Tree and navigation (read helpers)

### Get folder tree

`GET /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/tree`

**Permission:** `folder:read`

**Query:** `depth` (default 3, max 10)

**Response:** Nested folder nodes with document counts (not full document payloads).

---

### Breadcrumb

`GET /workspaces/{workspace_id}/knowledge-bases/{knowledge_base_id}/folders/{folder_id}/breadcrumb`

**Permission:** `folder:read`

**Response:** Ordered ancestry from KB root to folder.

---

## OpenAPI tags

| Tag | Endpoints |
| --- | --- |
| `knowledge-bases` | KB CRUD and lifecycle |
| `folders` | Folder hierarchy |
| `documents` | Document CRUD and lifecycle |
| `document-versions` | Version history and download |
| `uploads` | Upload sessions and bulk |

## Dependencies

| Dependency | Usage |
| --- | --- |
| Identity provider | Resolve `user_id` for audit |
| File storage adapter | Staging and permanent object storage |
| Authorization service | Permission and ACL evaluation |
| Indexing pipeline | Subscribes to version events (async) |

## Non-functional requirements

| Area | Target |
| --- | --- |
| List latency | p95 < 300 ms for 100 items |
| Upload initiation | p95 < 500 ms |
| Availability | Consistent with platform SLA |
| Audit | All mutating commands emit audit events |
| Rate limits | Upload initiation: 60/min per user per workspace (configurable) |
