# Knowledge Module

> **Spec:** 008-frontend  
> **Authority:** Knowledge tree, upload, metadata, and processing status screens

## Module purpose

Let operators manage knowledge bases, folder trees, document uploads, metadata, and processing/indexing status before content is usable in Chat and Evaluation.

---

## Screen K1 — Knowledge base list

### Purpose

Browse and create workspace knowledge bases.

### Wireframe

```text
┌─────────────────────────────────────────────────────────────┐
│ Knowledge bases                         [Create knowledge base] │
│ Search [____________]   Status [All ▾]                      │
├─────────────────────────────────────────────────────────────┤
│ Name              Status     Docs   Language   Updated      │
│ Policies KB       active     42     fa         2h ago   →   │
│ Onboarding        draft       3     en         1d ago   →   │
│ Archive 2024      archived    9     fa         3w ago   →   │
└─────────────────────────────────────────────────────────────┘
```

### Components

`PageHeader`, `SearchField`, `StatusFilter`, `DataTable`, `StatusChip`, `CreateKnowledgeBaseDialog`

### States

| State | UI |
| --- | --- |
| Loading | Table skeleton (5 rows) |
| Success | Paginated table |
| Empty | “No knowledge bases yet” + Create CTA |
| Error | Inline error + Retry |

### API endpoints

| Action | Method / path |
| --- | --- |
| List | `GET /api/v1/workspaces/{workspace_id}/knowledge-bases` |
| Create | `POST /api/v1/workspaces/{workspace_id}/knowledge-bases` |

### Loading / Errors / Empty

- Loading: skeleton; keep header actions disabled until first load completes.
- Errors: show envelope `error.code` (`forbidden`, `internal_error`).
- Empty: illustration-free copy + primary Create button.

---

## Screen K2 — Knowledge browser (tree + content)

### Purpose

Navigate folders/documents and open detail in context.

### Wireframe

```text
┌──────────────────┬───────────────────────────────┬──────────────────┐
│ Policies KB  ▾   │  Folder: HR / Leave            │ Document         │
│ [Upload] [+Folder]│  Search [________]            │ Leave Policy.pdf │
│                  │                               │ Status: active   │
│ ▼ HR             │ Title            Status  Lang │ Lang: fa         │
│   ▼ Leave        │ Leave Policy.pdf indexed  fa  │ Tags: leave,hr   │
│     Leave Policy │ Handbook.docx    processing   │                  │
│   Benefits       │ FAQ.md           failed   !   │ [Edit metadata]  │
│ ▶ Legal          │                               │ [Versions]       │
└──────────────────┴───────────────────────────────┴──────────────────┘
```

Three panes (desktop): **Tree | Document list | Detail inspector**.

### Components

`KnowledgeBaseSelector`, `FolderTree`, `DocumentList`, `DocumentInspector`, `UploadDrawer`, `CreateFolderDialog`, `ProcessingStatusBadge`

### States

| State | UI |
| --- | --- |
| Loading tree | Tree skeleton |
| Loading docs | List skeleton |
| Empty folder | “This folder has no documents” + Upload |
| Empty KB | “Add a folder or upload a document” |
| Selection none | Inspector: “Select a document” |
| Error | Pane-level error banners (do not block other panes if independent) |

### API endpoints

| Action | Method / path |
| --- | --- |
| Get KB | `GET .../knowledge-bases/{knowledge_base_id}` |
| List folders | `GET .../knowledge-bases/{kb_id}/folders` |
| Create folder | `POST .../knowledge-bases/{kb_id}/folders` |
| List documents | `GET .../knowledge-bases/{kb_id}/documents?folder_id=` |
| Get document | `GET .../knowledge-bases/{kb_id}/documents/{document_id}` |

### Loading / Errors / Empty

- Prefer stale-while-revalidate for tree after mutations.
- `409 conflict` on duplicate names → field error on dialog.
- Soft-deleted / archived items hidden by default; optional “Show archived” toggle later (v1.1).

---

## Screen K3 — Upload

### Purpose

Upload one or more files into a folder via upload sessions.

### Wireframe

```text
┌──────────────────────────────────────────┐
│ Upload to: HR / Leave                    │
│ Drop files here or [Browse]              │
│                                          │
│ leave-v2.pdf     2.1 MB   ████████ 100%  │
│ handbook.docx    4.0 MB   ████░░░░  52%  │
│                                          │
│ [Cancel all]              [Done]         │
└──────────────────────────────────────────┘
```

### Components

`UploadDrawer`, `FileDropzone`, `UploadProgressRow`, `MimeHint`

### States

| State | UI |
| --- | --- |
| Idle | Dropzone |
| Uploading | Per-file progress |
| Completed | Checkmark; document appears in list |
| Failed | Error row + Retry / Cancel |
| Cancelled | Struck filename; removable |

### API endpoints

| Action | Method / path |
| --- | --- |
| Initiate upload | `POST .../documents/{document_id}/uploads` (or create-document-then-upload per API) |
| Upload part / bytes | Upload session endpoints from Knowledge API |
| Complete upload | Complete upload session |
| Create version | `POST .../documents/{document_id}/versions` with `upload_id` |

Exact upload multipart sequence follows [001 API — Uploads](../001-knowledge-management/API.md). UI must not invent alternate storage paths.

### Loading / Errors / Empty

- Block “Done” until all non-cancelled files reach terminal state.
- Unsupported MIME → immediate row error without starting session.

---

## Screen K4 — Document metadata

### Purpose

View and edit title, language, tags, classification, and custom metadata.

### Wireframe

```text
┌─────────────────────────────────────────────┐
│ Leave Policy.pdf                     [Save] │
│ Title        [Leave Policy____________]     │
│ Language     [fa ▾]                         │
│ Classification [public_internal ▾]          │
│ Tags         [leave] [hr] [+]               │
│ Custom metadata (JSON / key-value)          │
│ key: policy_area   value: leave             │
└─────────────────────────────────────────────┘
```

### Components

`MetadataForm`, `TagInput`, `LanguageSelect`, `JsonKeyValueEditor`, `UnsavedChangesGuard`

### States

| State | UI |
| --- | --- |
| Loading | Form skeleton |
| Dirty | Save enabled; navigate confirms discard |
| Saving | Save spinner; form locked |
| Saved | Toast “Metadata saved” |
| Read-only | Archived/deleted → fields disabled |

### API endpoints

| Action | Method / path |
| --- | --- |
| Get metadata | `GET .../documents/{document_id}/metadata` |
| Patch document | `PATCH .../documents/{document_id}` |
| Replace metadata | `PUT .../documents/{document_id}/metadata` |

### Loading / Errors / Empty

- Validation errors map to field messages (`validation_failed`).
- Empty custom metadata → “No custom fields” + Add field.

---

## Screen K5 — Processing status

### Purpose

Show document version pipeline state (uploaded → processing → indexed / failed).

### Wireframe

```text
┌──────────────────────────────────────────────────────────┐
│ Version v3 · Leave Policy.pdf                            │
│                                                          │
│ Step                Status                               │
│ Uploaded            done                                 │
│ Extracted           done                                 │
│ Chunked / Embedded  in progress …                        │
│ Indexed             pending                              │
│                                                          │
│ processing_status: processing                            │
│ Updated 12s ago                    [Refresh] [Retry*]    │
└──────────────────────────────────────────────────────────┘
```

\*Retry only when API reports `retryable: true`.

### Components

`VersionTimeline`, `ProcessingStatusBadge`, `FailureReasonAlert`, `PollIndicator`

### States

| State | UI |
| --- | --- |
| Polling | Subtle live region “Updating status…” every N seconds |
| Indexed | Success banner; enable “Ask in Chat” shortcut |
| Failed | Failure reason + retry if allowed |
| Stalled | If no change > threshold, show soft warning |

### API endpoints

| Action | Method / path |
| --- | --- |
| List versions | `GET .../documents/{document_id}/versions` |
| Get version | `GET .../documents/{document_id}/versions/{version_id}` |
| Status | `GET .../documents/{document_id}/versions/{version_id}/status` |

### Loading / Errors / Empty

- Initial load skeleton; subsequent polls silent unless value changes.
- Empty versions → “Upload a file to create the first version.”

## Module non-goals

- In-browser PDF/Office editors
- Full ECM permissions matrix UI
- Drag-drop reordering of arbitrary document ranks
- Bulk archive wizard (v1.1+)
