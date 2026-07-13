# Document Processing

> **Spec ID:** 002  
> **Status:** Draft  
> **Goal:** Turn uploaded files into clean Persian text ready for chunking.  
> **Scope:** Extraction and text normalization only — no chunking, embeddings, or retrieval.

## 1. Purpose

When a `DocumentVersion` is created from an upload (Feature 001), a background worker
extracts readable text, normalizes Persian content, detects language, and stores a single
extracted text artifact. Downstream chunking (future spec) reads that artifact.

This module sits between **Knowledge Management** and **Knowledge Indexing**:

```text
Upload complete → DocumentVersion (uploaded)
  → extract text
  → normalize Persian
  → write extracted/text.txt
  → DocumentVersion (extracted)
  → (future) chunking
```

The HTTP API does not change. Processing is async and idempotent per version.

---

## 2. Supported file types (v1)

| Format | Extensions | Extractor | Notes |
| --- | --- | --- | --- |
| Plain text | `.txt` | Direct read | UTF-8 required; UTF-16 accepted with conversion |
| Markdown | `.md` | Direct read | Strip minimal markup; keep paragraph breaks |
| HTML | `.html`, `.htm` | HTML parser | Remove scripts/styles; keep visible text |
| Word | `.docx` | DOCX parser | Paragraphs and tables as plain text |
| PDF | `.pdf` | PDF text layer | Text-based PDFs only in v1 |

**Not in v1:** scanned PDFs, images, `.doc`, `.rtf`, archives, spreadsheets.

Reject unsupported types during upload validation (Feature 001). If extraction discovers
an unreadable file (e.g. scanned PDF with no text layer), mark the version `failed`.

Maximum file size follows Feature 001 (50 MB default).

---

## 3. Processing pipeline

### Trigger

A worker consumes `DocumentVersionUploaded` (or polls versions in `uploaded` status).

### Steps

```mermaid
flowchart LR
    A[Load original from storage] --> B[Detect format]
    B --> C[Extract raw text]
    C --> D[Detect language]
    D --> E[Normalize Persian]
    E --> F[Extract metadata]
    F --> G[Write text.txt]
    G --> H[Update version status]
```

| Step | Action |
| --- | --- |
| 1. Claim job | Set `processing_status` → `extracting`; skip if already processing |
| 2. Load file | Read `storage_key_original` from object storage |
| 3. Extract | Run format-specific extractor; produce one UTF-8 string |
| 4. Language | Detect primary language; record confidence |
| 5. Normalize | Apply Persian normalization rules (Section 4) |
| 6. Metadata | Attach lightweight metadata (Section 5) |
| 7. Store | Write `extracted/text.txt` and optional `extracted/meta.json` |
| 8. Complete | Set `processing_status` → `extracted`; set `storage_key_extracted` |

### Status transitions

Uses existing `DocumentVersion` lifecycle:

| From | To | Meaning |
| --- | --- | --- |
| `uploaded` | `extracting` | Worker claimed job |
| `extracting` | `extracted` | Text artifact written |
| `extracting` | `failed` | Unrecoverable error |
| `failed` | `uploaded` | Manual retry (re-queue) |

Do not implement chunking or `indexed` transitions in this spec.

### Idempotency

- One extraction output per `document_version_id`.
- Re-running on an already `extracted` version is a no-op unless `force_reprocess` flag is set (admin-only, future).
- Object keys are immutable per version; reprocessing overwrites `text.txt` in place.

### Concurrency

- At most one active extraction job per `document_version_id`.
- Workers may process different versions in parallel.

---

## 4. Persian normalization

Primary audience is Persian (`fa`) documents. Normalization runs on all extracted text
but is essential for Persian quality.

### Rules (apply in order)

| Rule | Example | Rationale |
| --- | --- | --- |
| Unicode NFC | Compose combining characters | Consistent matching |
| Arabic → Persian letters | `ي` → `ی`, `ك` → `ک` | Standard Persian orthography |
| Persian digits → Latin | `۱۲۳` → `123` | Consistent numbers in RAG (configurable) |
| Punctuation unify | `؟` kept; fancy quotes → `"` | Readable plain text |
| Zero-width cleanup | Remove ZWNJ abuse where safe | Reduce token noise; **keep** valid ZWNJ in compound words when followed by Persian letters |
| Whitespace | Collapse runs of spaces; normalize line endings to `\n` | Clean chunk boundaries |
| Strip control chars | Remove `\x00`–`\x1f` except `\n`, `\t` | Safety |
| Paragraph breaks | Preserve blank lines between paragraphs | Chunking hint |

### What we do not do in v1

- Transliteration (Finglish → Persian)
- Spell correction
- Sentence segmentation
- Diacritic restoration

### Mixed-language documents

If detection finds substantial English (or other) passages, still apply Persian rules
only to Persian script ranges; leave Latin segments unchanged.

---

## 5. Metadata extraction

Store a small JSON sidecar at `extracted/meta.json` (optional but recommended).

| Field | Type | Description |
| --- | --- | --- |
| `extractor` | string | Library/name + version used |
| `extracted_at` | datetime | UTC timestamp |
| `char_count` | int | Length after normalization |
| `line_count` | int | Line count |
| `detected_language` | string | BCP-47 primary language |
| `language_confidence` | float | 0.0–1.0 |
| `declared_language` | string | From `Document.declared_language` |
| `language_match` | bool | Detected matches declared within policy |
| `page_count` | int | PDF/DOCX only; null otherwise |
| `title_guess` | string | First heading or filename stem |
| `warnings` | string[] | Non-fatal issues (e.g. `"empty_page_3"`) |

Do not extract PII-specific fields. Do not store full document structure trees in v1.

---

## 6. Language detection

| Input | Method |
| --- | --- |
| Short text (&lt; 100 chars) | Use `Document.declared_language`; confidence = 0.5 |
| Longer text | Lightweight detector (e.g. `langdetect` or fastText) on first 10 KB + sample from middle |

### Policy

| Result | Action |
| --- | --- |
| Detected `fa` | Proceed; full Persian normalization |
| Detected `en` or other | Proceed; skip Persian-specific letter swaps; still NFC + whitespace cleanup |
| Detection uncertain (&lt; 0.7 confidence) | Proceed; add warning; prefer `declared_language` for metadata |
| Mismatch with `declared_language` | Do not fail; set `language_match: false` and warning |

Language detection informs metadata and normalization scope. It does not block extraction
in v1 unless the file is empty.

---

## 7. Output format

### Primary artifact: `text.txt`

| Property | Value |
| --- | --- |
| Encoding | UTF-8 (no BOM) |
| Line endings | `\n` |
| Content | Plain text only — no HTML, markdown, or JSON |
| Storage path | Per `docs/data/STORAGE_STRATEGY.md`: `.../version/{id}/extracted/text.txt` |

### Sidecar: `meta.json`

UTF-8 JSON object as defined in Section 5.

### Database updates

On success, update `DocumentVersion`:

- `processing_status` → `extracted`
- `storage_key_extracted` → key to `text.txt`
- `failure_reason` → null

`content_hash` on the version remains the hash of the **original** upload, not extracted text.

### Contract for chunking (future)

Chunking reads `text.txt` only. It expects:

- Valid UTF-8
- Persian normalized per this spec when `detected_language` is `fa`
- Paragraphs separated by blank lines where possible

---

## 8. Error handling

### Failure categories

| Code | When | Version status | Retryable |
| --- | --- | --- | --- |
| `empty_content` | No extractable text | `failed` | No |
| `encrypted_pdf` | Password-protected PDF | `failed` | No |
| `unsupported_format` | Format not in v1 | `failed` | No |
| `corrupt_file` | Parser cannot read file | `failed` | No |
| `storage_read_error` | Original missing/unreadable | `failed` | Yes |
| `storage_write_error` | Cannot write extracted text | `failed` | Yes |
| `extraction_timeout` | Exceeds per-file timeout (default 120s) | `failed` | Yes |
| `unknown_error` | Unexpected exception | `failed` | Yes |

Store `failure_reason` as the code (not stack traces). Log full exception server-side with
`document_version_id` and `correlation_id`.

### Retry policy

| Attempt | Delay |
| --- | --- |
| 1st retry | 30 seconds |
| 2nd retry | 5 minutes |
| 3rd retry | 30 minutes |

After 3 failures, stop auto-retry; version stays `failed` until manual retry.

### Partial success

Not supported in v1. Extraction is all-or-nothing: either `text.txt` is written or status is `failed`.

### Observability

Log structured events:

- `extraction_started`
- `extraction_completed` (with `char_count`, `detected_language`)
- `extraction_failed` (with `failure_reason`)

---

## 9. Module boundaries

### In scope

- Format detection and text extraction
- Persian normalization
- Language detection and metadata sidecar
- Worker job + status updates on `DocumentVersion`
- Object storage read/write for extracted artifacts

### Out of scope

- Chunking, embeddings, vector index
- OCR / scanned documents
- API endpoints (processing is internal)
- Changing upload or knowledge management APIs
- Auth, tenancy, or permission checks (worker uses system context with version IDs)

### Suggested package location

```text
backend/src/rag_enterprise/processing/
  extractors/       # pdf, docx, html, plain
  normalization/    # Persian rules
  metadata/         # language + meta.json builder
  worker/           # job handler
```

Follow existing patterns: `Result[T]`, structured logging, settings from `core/config`,
no business logic in extractors beyond text transformation.

---

## 10. Acceptance criteria (summary)

1. A uploaded `.txt`, `.md`, `.html`, `.docx`, or text-based `.pdf` in Persian becomes
   `extracted/text.txt` with normalized Persian letters and stable UTF-8.
2. `DocumentVersion.processing_status` moves `uploaded` → `extracting` → `extracted`.
3. `meta.json` includes detected language and char count.
4. Empty or scanned PDF fails with `empty_content` or `corrupt_file` and does not block other jobs.
5. Re-processing the same version without `force_reprocess` does not duplicate work.
6. Output is suitable input for a future chunker without further cleaning.

---

## Related documents

- [001 Knowledge Management](../001-knowledge-management/README.md)
- [Storage Strategy](../../docs/data/STORAGE_STRATEGY.md)
- [Entity Lifecycle — Document Version](../../docs/domain/ENTITY_LIFECYCLE.md)
