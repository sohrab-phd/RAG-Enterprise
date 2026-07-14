# Golden Dataset

> **Spec:** 007-evaluation-framework  
> **Authority:** Dataset contract for offline RAG evaluation

## 1. Purpose

A **golden dataset** is a versioned set of questions with expected answers and citations,
used to measure retrieval and generation. Datasets are fixtures, not live production exports.

## 2. Dataset versioning

| Field | Description |
| --- | --- |
| `dataset_id` | Stable name, e.g. `kb-hr-fa-smoke` |
| `dataset_version` | Semver or date tag, e.g. `1.0.0` or `2026-07-14` |
| `knowledge_base_id` | Target KB the corpus was indexed under (or fixture KB id) |
| `language_default` | Primary language of the set (`fa`, `en`, or `mixed`) |
| `created_at` | UTC timestamp |
| `notes` | Optional changelog note |

Storage (conceptual, per [STORAGE_STRATEGY.md](../../docs/data/STORAGE_STRATEGY.md)):

```text
evaluation/{evaluation_or_dataset_id}/
  dataset.jsonl
  manifest.json
```

Format: **JSONL** — one question record per line. UTF-8, no BOM.

## 3. Question record schema

Every line is one JSON object:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Yes | Stable question id within the dataset (e.g. `hr-leave-001`) |
| `question` | string | Yes | User question text |
| `expected_answer` | string | Yes* | Reference answer for grounded cases; empty string when abstention is expected |
| `expected_citations` | CitationRef[] | Yes | Expected evidence; empty when abstention is expected |
| `knowledge_base_id` | UUID / string | Yes | KB under evaluation (must match experiment KB unless noted) |
| `difficulty` | string | Yes | `easy` \| `medium` \| `hard` |
| `language` | string | Yes | `fa` \| `en` (question language) |
| `tags` | string[] | Yes | Free-form labels (e.g. `leave`, `abstain`, `multilingual`) |
| `expect_abstention` | bool | No | Default `false`. When `true`, generation should abstain |
| `notes` | string | No | Author guidance; ignored by runner |

\*When `expect_abstention` is `true`, `expected_answer` may be empty; metrics use abstention labels instead of answer similarity.

### CitationRef

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `chunk_id` | UUID / string | Yes* | Expected retrieved / cited chunk |
| `document_id` | UUID / string | No | Expected document if chunk ids differ across re-chunk runs |
| `document_version_id` | UUID / string | No | Pin source version when available |
| `rank_hint` | int | No | Preferred retrieval rank (1 = best); optional for scoring |

\*If re-chunking invalidates `chunk_id`, authors may use `document_id` + passage fingerprint in `notes` and update the dataset after re-index. v1 prefers stable fixture KBs that are not re-chunked between dataset versions.

## 4. Example record

```json
{
  "id": "hr-leave-001",
  "question": "مرخصی سالانه چند روز است؟",
  "expected_answer": "مرخصی سالانه ۲۰ روز کاری است.",
  "expected_citations": [
    {
      "chunk_id": "018f0000-0000-7000-8000-00000000c001",
      "document_id": "018f0000-0000-7000-8000-00000000d001"
    }
  ],
  "knowledge_base_id": "018f0000-0000-7000-8000-00000000kb01",
  "difficulty": "easy",
  "language": "fa",
  "tags": ["leave", "hr", "fa"],
  "expect_abstention": false
}
```

Abstention example:

```json
{
  "id": "hr-unknown-001",
  "question": "قیمت سهام شرکت چقدر است؟",
  "expected_answer": "",
  "expected_citations": [],
  "knowledge_base_id": "018f0000-0000-7000-8000-00000000kb01",
  "difficulty": "easy",
  "language": "fa",
  "tags": ["abstain", "out-of-corpus"],
  "expect_abstention": true
}
```

## 5. Authoring rules

| Rule | Description |
| --- | --- |
| Synthetic first | Prefer synthetic HR/policy-style fixtures |
| No secrets | No credentials, PII, or customer data |
| Language labeled | Every question has explicit `language` |
| Tags required | At least one tag (can be `uncategorized`) |
| One KB | All records in a dataset version share one primary KB unless the manifest documents otherwise |
| Immutable version | Published `dataset_version` is read-only; edits require a new version |

## 6. Manifest (`manifest.json`)

```json
{
  "dataset_id": "kb-hr-fa-smoke",
  "dataset_version": "1.0.0",
  "knowledge_base_id": "...",
  "question_count": 25,
  "languages": ["fa", "en"],
  "created_at": "2026-07-14T00:00:00Z",
  "notes": "Smoke set for Phase 6 framework validation"
}
```

## 7. Out of scope

- Labeling UI
- Auto-generation of golden answers via LLM as ground truth without human review
- Multi-KB federated datasets in v1
