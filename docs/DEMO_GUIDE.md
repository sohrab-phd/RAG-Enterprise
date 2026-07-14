# Demo Guide

> **Purpose:** Entry point for the official Version 1.0.0 demonstration workspace.  
> **Release:** 1.0.0  
> **Corpus authority:** [demo/README.md](../demo/README.md) (do not duplicate policies here).

## Purpose

Help reviewers and newcomers run the public Persian **نوین‌پرداز** demo using the
supported operator workflow end to end.

## Audience

Demo operators, PR reviewers, and public GitHub visitors.

## Supported operator workflow

```text
Create KB
  → Upload documents
  → Process & Index
  → Publish
  → Ask questions
  → View citations
  → Run evaluation
  → View Evaluation Dashboard
```

### Steps

1. **Create KB** — In Knowledge, create a knowledge base (default language `fa`).
   Status starts as `draft`.
2. **Upload documents** — Import all four files from `demo/knowledge/`.
3. **Process & Index** — For each document, click **Process & Index** (or call
   `POST .../documents/{document_id}/process`) until status is `indexed`.
4. **Publish** — On the Knowledge list, click **Publish** so the KB becomes
   `active` (required for retrieval and chat).
5. **Ask questions** — Open Chat, select the demo KB, use prompts from
   `demo/questions/suggested-questions-fa.md`.
6. **View citations** — Confirm grounded answers show citation evidence.
7. **Run evaluation** — Prepare and run the offline Feature 007 set under
   `demo/evaluation/` (see [demo/README.md](../demo/README.md)).
8. **View Evaluation Dashboard** — Inspect runs in the frontend Evaluation module.

Details, company facts, and citation ID rebinding:
[demo/README.md](../demo/README.md).

## Artifacts

| Path | Contents |
| --- | --- |
| [demo/knowledge/](../demo/knowledge/) | Employee handbook, leave, remote work, travel policies |
| [demo/questions/](../demo/questions/) | Suggested Chat questions |
| [demo/evaluation/](../demo/evaluation/) | `manifest.json`, `evaluation.jsonl`, ID map |

## Related documents

- [Evaluation Guide](EVALUATION_GUIDE.md)
- [Process & Index](backend/PROCESS_AND_INDEX.md)
- [Knowledge management](backend/KNOWLEDGE_MANAGEMENT.md)
- [E2E Happy Path](backend/E2E_HAPPY_PATH.md)
- [Feature Map](FEATURE_MAP.md)
- [Documentation index](README.md)
