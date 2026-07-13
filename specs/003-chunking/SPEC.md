# Chunking

> **Spec ID:** 003  
> **Status:** Draft  
> **Goal:** Convert clean extracted text into high-quality chunks ready for embedding.  
> **Scope:** Chunk generation only — no embeddings, vector index, retrieval, or API.

## 1. Purpose

Feature 002 (Document Processing) produces a single normalized UTF-8 text artifact per
`DocumentVersion`. Feature 003 splits that text into ordered, immutable chunks that
preserve source position and are suitable for embedding in a later indexing stage.

Chunking sits between **Document Processing** and **Knowledge Indexing**:

```text
DocumentVersion (extracted)
  → read extracted/text.txt
  → select chunking strategy
  → generate Chunk objects
  → DocumentVersion (chunked)
  → (future) embedding
```

The HTTP API does not change. Chunking runs asynchronously and idempotently per version.

### Goals

| Goal | Description |
| --- | --- |
| Retrieval quality | Chunks are semantically coherent units sized for embedding models |
| Citation fidelity | Character offsets map back to the extracted text for source highlighting |
| Reproducibility | Same text + strategy + parameters → same chunk set |
| Simplicity | Rule-based splitting only; no LLM or embedding-driven boundaries |

### Non-goals

- Semantic chunking (embedding similarity splits)
- LLM-assisted chunking
- Embedding generation or vector storage
- Retrieval, reranking, or citation rendering
- Database schema, ORM models, or persistence design
- Re-normalization of text (processing output is trusted as-is)

---

## 2. Input contract

Chunking reads the extracted text artifact produced by Feature 002.

| Property | Requirement |
| --- | --- |
| Source | `extracted/text.txt` for the target `DocumentVersion` |
| Encoding | UTF-8 (no BOM) |
| Line endings | `\n` |
| Preprocessing | Already normalized per Feature 002; chunker must not alter characters |
| Paragraph hints | Blank lines (`\n\n`) separate paragraphs where extraction preserved them |
| Version status | `DocumentVersion.processing_status` must be `extracted` |

Optional sidecar `extracted/meta.json` may supply `detected_language` for chunk-level
language tagging. Chunking does not require the sidecar to run.

### Trigger

A worker consumes versions in `extracted` status (or a `DocumentVersionExtracted` event)
and claims the chunking job.

---

## 3. Supported strategies

Three strategies are supported in v1. The caller selects one; default is
**paragraph-aware**.

| Strategy | Key | When to use |
| --- | --- | --- |
| Paragraph-aware | `paragraph` | **Default.** General documents with paragraph breaks |
| Fixed-size | `fixed` | Uniform chunk sizes; weak structure |
| Heading-aware | `heading` | Documents with clear section headings |

**Not in v1:** semantic chunking, LLM chunking, sentence-transformer boundaries,
table-aware or code-block-aware splitting.

### 3.1 Paragraph-aware (default)

1. Split text into **paragraph units** on blank lines (`\n\n` or more).
2. Greedily merge adjacent paragraphs into a chunk until adding the next paragraph
   would exceed `max_chunk_chars`.
3. If a single paragraph exceeds `max_chunk_chars`, split it (Section 4.3).
4. Apply **overlap** between consecutive chunks when a paragraph was split or when
   merging produced a hard boundary (Section 4.2).

Preserves reading order and respects natural paragraph boundaries where possible.

### 3.2 Fixed-size

1. Walk the text left-to-right in windows of `target_chunk_chars`.
2. Prefer breaking at the last blank line or whitespace before the window end.
3. If no soft break exists within the last 15% of the window, hard-break at
   `target_chunk_chars`.
4. Advance the next window start by `target_chunk_chars - overlap_chars`.

Ignores document structure. Use only when structure is unknown or uniformly dense.

### 3.3 Heading-aware

1. Detect **section boundaries** at lines matching heading heuristics (Section 3.4).
2. Each section becomes a candidate region with an optional `heading` value (the heading
   line text, trimmed).
3. Within each section, apply **paragraph-aware** rules (Section 3.1).
4. All chunks in a section inherit the section `heading` unless split across sections.

Best for markdown exports, DOCX-derived text with short title lines, or documents where
the first line of a blank-line-separated block acts as a title.

### 3.4 Heading detection heuristics (v1)

A line starts a new section when **all** of the following hold:

| Rule | Condition |
| --- | --- |
| Position | First line of a blank-line-separated block, or line 0 of the document |
| Length | ≤ 120 characters |
| Markdown | Starts with `#` followed by space (if markdown markers remain in extracted text) |
| Title-like | Does not end with `.`, `?`, or `!` **or** matches markdown heading pattern |

If no headings are detected, heading-aware **degrades** to paragraph-aware and emits a
warning `no_headings_detected` (Section 8).

Malformed heading structure (e.g. nested markdown without blank lines) is handled in
Section 8 — chunking continues with best-effort boundaries.

---

## 4. Chunk sizing

Recommended defaults (configurable per knowledge base in a future indexing spec):

| Parameter | Recommended | Range | Description |
| --- | --- | --- | --- |
| `target_chunk_chars` | 1000 | 800–1200 | Desired chunk body size |
| `max_chunk_chars` | 1200 | ≤ 1500 | Hard upper bound before forced split |
| `min_chunk_chars` | 50 | 20–100 | Minimum non-whitespace characters to emit a chunk |
| `overlap_chars` | 125 | 100–150 | Characters repeated at the start of the next chunk |

`target_chunk_chars` guides merging and window sizing. `max_chunk_chars` is the hard
ceiling for any single chunk.

### 4.1 Merging undersized paragraphs

When paragraph-aware or heading-aware merging would produce a chunk below
`min_chunk_chars`, merge with the next paragraph unless that would exceed
`max_chunk_chars`. If the document ends with a trailing undersized fragment, attach it
to the previous chunk when combined size ≤ `max_chunk_chars`; otherwise emit as its own
chunk if it meets `min_chunk_chars`.

### 4.2 Overlap

Overlap applies when:

- A paragraph was split across chunks (Section 4.3)
- Fixed-size strategy advances the window

The next chunk begins with the last `overlap_chars` of the previous chunk's text
(sliced on Unicode code points, not UTF-16 units). Overlap text is included in
`start_char` / `end_char` accounting — offsets always refer to positions in the **original
extracted text**, and overlapping regions may appear in adjacent chunks.

### 4.3 Oversized paragraphs

When a single paragraph exceeds `max_chunk_chars`:

```text
1. Try sentence boundaries: split after `.`, `?`, `!`, `؟`, or `۔`
   followed by whitespace, working backward from max_chunk_chars.
2. If no boundary in the last 30% of the window, split at the last whitespace
   before max_chunk_chars.
3. If no whitespace, hard-split at max_chunk_chars (code-point boundary).
4. Repeat for the remainder with overlap_chars applied.
```

Sentence splitting is best-effort. Persian and English punctuation are both considered.
Do not split inside a Unicode combining character sequence.

---

## 5. Chunk metadata and output contract

Chunking returns an ordered list of **Chunk** value objects. These are the contract for
the embedding stage. No database schema or ORM is defined in this spec.

### 5.1 Chunk object

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `document_version_id` | UUID | Yes | Parent version; every chunk belongs to exactly one version |
| `chunk_index` | int | Yes | Zero-based sequence in reading order (`0 … n-1`) |
| `text` | string | Yes | Chunk body; non-empty after strip |
| `start_char` | int | Yes | Inclusive start offset in extracted text (code points) |
| `end_char` | int | Yes | Exclusive end offset in extracted text |
| `heading` | string | No | Section heading when strategy supplies one |
| `content_hash` | string | Yes | SHA-256 hex digest of `text` encoded as UTF-8 |
| `language` | string | No | `fa`, `en`, or `unknown`; copied from version metadata or per-chunk detection future |
| `strategy` | string | Yes | `paragraph`, `fixed`, or `heading` |

**Invariants:**

- `0 ≤ start_char < end_char ≤ len(extracted_text)`
- `text` equals `extracted_text[start_char:end_char]` exactly (no duplicated overlap in stored text)
- `chunk_index` is contiguous with no gaps
- `content_hash` = `sha256(text.encode("utf-8")).hexdigest()`

**Overlap rule:** Overlap affects where the next chunk starts:
`next.start_char = max(0, prev.end_char - overlap_chars)`. Each chunk's `text` is a
contiguous slice of the source; embedding consumers receive non-duplicated spans.

### 5.2 Chunking result envelope

| Field | Type | Description |
| --- | --- | --- |
| `document_version_id` | UUID | Version that was chunked |
| `strategy` | string | Strategy applied |
| `chunks` | Chunk[] | Ordered chunk list |
| `chunk_count` | int | `len(chunks)` |
| `warnings` | string[] | Non-fatal issues |
| `parameters` | object | Snapshot of sizing parameters used |

### 5.3 Version reference

Every chunk carries `document_version_id`. Downstream indexing persists this FK;
chunking itself does not write to the database.

When a new `DocumentVersion` is published, a **new** chunk set is generated. Chunks are
never mutated or moved between versions.

---

## 6. Business rules

| ID | Rule |
| --- | --- |
| CH-01 | Chunks belong to exactly one `DocumentVersion`. |
| CH-02 | Chunks are immutable once created. Corrections require a new document version. |
| CH-03 | A new document version produces a new chunk set; prior version chunks are superseded by indexing, not overwritten. |
| CH-04 | Empty chunks are never created. Whitespace-only spans are skipped. |
| CH-05 | Chunk order matches source text order (`chunk_index` ascending ⇔ `start_char` ascending). |
| CH-06 | Unicode in chunk `text` matches the extracted text substring exactly — no NFC, trimming, or normalization in the chunker. |
| CH-07 | Leading/trailing whitespace may be trimmed from `text` only if `start_char`/`end_char` are adjusted to match the trimmed span. |
| CH-08 | Re-chunking the same version with the same parameters is idempotent. |
| CH-09 | At most one active chunking job per `document_version_id`. |
| CH-10 | `DocumentVersion.processing_status` transitions: `extracted` → `chunking` → `chunked` (or `failed`). |

---

## 7. Processing flow

```mermaid
flowchart LR
    A[Load extracted text] --> B[Validate non-empty]
    B --> C[Select strategy]
    C --> D[Split into chunks]
    D --> E[Assign offsets and hashes]
    E --> F[Build Chunk list]
    F --> G[Return result]
```

| Step | Action |
| --- | --- |
| 1. Claim job | Set `processing_status` → `chunking` |
| 2. Load text | Read `extracted/text.txt` |
| 3. Validate | Reject empty or whitespace-only input |
| 4. Chunk | Apply selected strategy and sizing parameters |
| 5. Finalize | Compute `content_hash`, assign `chunk_index` |
| 6. Complete | Set `processing_status` → `chunked`; emit `ChunksCreated` (future) |

Chunk artifacts may optionally be written to object storage as `chunked/chunks.jsonl`
(one JSON object per line) in a future persistence spec. This spec defines the in-memory
contract only.

---

## 8. Error handling

### Failure categories

| Code | When | Version status | Retryable |
| --- | --- | --- | --- |
| `empty_document` | No non-whitespace text | `failed` | No |
| `unsupported_strategy` | Strategy not in v1 set | `failed` | No |
| `storage_read_error` | Cannot read extracted text | `failed` | Yes |
| `chunking_timeout` | Exceeds per-version timeout (default 60s) | `failed` | Yes |
| `unknown_error` | Unexpected exception | `failed` | Yes |

Store `failure_reason` as the code. Log `document_version_id` and `correlation_id`
server-side.

### Warnings (non-fatal)

| Code | When |
| --- | --- |
| `no_headings_detected` | Heading-aware found no sections; fell back to paragraph-aware |
| `malformed_heading_structure` | Headings detected but inconsistently separated; best-effort split |
| `oversized_paragraph_split` | One or more paragraphs required hard splitting |
| `short_document` | Entire document fits in one chunk below `target_chunk_chars` |

### Retry policy

| Attempt | Delay |
| --- | --- |
| 1st retry | 30 seconds |
| 2nd retry | 5 minutes |
| 3rd retry | 30 minutes |

After 3 failures, stop auto-retry until manual retry from `failed` → `extracted`.

### Partial success

Not supported. Either the full chunk list is produced or the version is `failed`.

---

## 9. Module boundaries

### In scope

- Strategy implementations (paragraph, fixed, heading)
- Character-offset tracking and `content_hash` generation
- Pure chunking service: input text + parameters → chunk list
- Status transition hooks on `DocumentVersion` (worker integration)

### Out of scope

- Embeddings, pgvector, retrieval configuration
- HTTP API endpoints
- PostgreSQL tables and ORM models
- Semantic or LLM chunking
- OCR-specific layout chunking
- Auth and tenancy (worker uses system context with version IDs)

### Suggested package location

```text
backend/src/rag_enterprise/chunking/
  strategies/       # paragraph.py, fixed.py, heading.py
  models.py         # Chunk, ChunkingResult
  service.py        # ChunkingService
  exceptions.py
```

Follow existing patterns: `Result[T]`, structured logging, settings from `core/config`.
Keep strategies as pure functions over `str` where possible.

---

## 10. Acceptance criteria

### AC-01: Paragraph document

**Given** a Persian document with paragraphs separated by blank lines  
**And** total length ≈ 3000 characters  
**When** chunking runs with strategy `paragraph` and default sizing  
**Then** multiple chunks are returned  
**And** each chunk length is ≤ `max_chunk_chars`  
**And** `chunk_index` values are contiguous from 0  
**And** concatenating non-overlapping spans in order recovers the source text

### AC-02: Markdown-style sections

**Given** extracted text with `# عنوان\n\nمتن بخش` section structure  
**When** chunking runs with strategy `heading`  
**Then** chunks include `heading` for the section title  
**And** body text does not include the `#` marker in `heading` (trimmed plain title)

### AC-03: Long single paragraph

**Given** a document with one paragraph longer than `max_chunk_chars`  
**When** chunking runs with strategy `paragraph`  
**Then** the paragraph is split into multiple chunks  
**And** a warning `oversized_paragraph_split` is recorded  
**And** no chunk exceeds `max_chunk_chars`

### AC-04: Empty file

**Given** extracted text that is empty or whitespace only  
**When** chunking runs  
**Then** chunking fails with `empty_document`  
**And** `processing_status` becomes `failed`

### AC-05: Mixed Persian–English text

**Given** a document with alternating Persian and English paragraphs  
**When** chunking runs with strategy `paragraph`  
**Then** chunks preserve original Unicode exactly (Persian ی/ک, ZWNJ, Latin letters)  
**And** offsets point to correct spans in the source  
**And** `content_hash` matches each chunk's UTF-8 bytes

### AC-06: Fixed-size strategy

**Given** a 5000-character document with no blank lines  
**When** chunking runs with strategy `fixed`  
**Then** chunk sizes are approximately `target_chunk_chars`  
**And** consecutive chunks share `overlap_chars` of context at boundaries

### AC-07: Unsupported strategy

**Given** strategy `semantic`  
**When** chunking is requested  
**Then** chunking fails with `unsupported_strategy`

### AC-08: Idempotency

**Given** a version already in `chunked` status  
**When** chunking runs again without `force_rechunk`  
**Then** the job is a no-op (or returns the same chunk set)

### AC-09: New version isolation

**Given** document version A and newer version B of the same document  
**When** both are chunked  
**Then** each version's chunks reference only their own `document_version_id`  
**And** chunk sets are independent

---

## 11. Observability

Log structured events:

| Event | Fields |
| --- | --- |
| `chunking_started` | `document_version_id`, `strategy` |
| `chunking_completed` | `document_version_id`, `chunk_count`, `warnings` |
| `chunking_failed` | `document_version_id`, `failure_reason` |

---

## 12. Related documents

- [002 Document Processing](../002-document-processing/SPEC.md)
- [001 Knowledge Management](../001-knowledge-management/README.md)
- [Entity Lifecycle — Document Version](../../docs/domain/ENTITY_LIFECYCLE.md)
- [Data Lifecycle](../../docs/data/DATA_LIFECYCLE.md)
- [Relationships — DocumentVersion → Chunk](../../docs/data/RELATIONSHIPS.md)
- [Indexing Strategy](../../docs/data/INDEXING_STRATEGY.md)
- [Storage Strategy](../../docs/data/STORAGE_STRATEGY.md)
