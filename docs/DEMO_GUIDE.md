# Demo Guide

> **Purpose:** Entry point for the official Version 1 demonstration workspace.  
> **Corpus authority:** [demo/README.md](../demo/README.md) (do not duplicate policies here).

## Purpose

Help reviewers and newcomers run the public Persian **نوین‌پرداز** demo end to end:
import documents, index, chat, then evaluate.

## Audience

Demo operators, PR reviewers, and public GitHub visitors.

## Steps (summary)

1. **Import** the four files under `demo/knowledge/` into an **active** knowledge base.  
2. **Index** until document versions are retrieval-ready.  
3. **Open Chat** and try prompts from `demo/questions/suggested-questions-fa.md`.  
4. **Run evaluation** with `demo/evaluation/` (Feature 007 layout).

Full commands, company fact table, and citation rebinding notes:
[demo/README.md](../demo/README.md).

## Artifacts

| Path | Contents |
| --- | --- |
| [demo/knowledge/](../demo/knowledge/) | Employee handbook, leave, remote work, travel policies |
| [demo/questions/](../demo/questions/) | Suggested Chat questions |
| [demo/evaluation/](../demo/evaluation/) | `manifest.json`, `evaluation.jsonl`, ID map |

## Related documents

- [Evaluation Guide](EVALUATION_GUIDE.md)
- [E2E Happy Path](backend/E2E_HAPPY_PATH.md)
- [Feature Map](FEATURE_MAP.md)
- [Documentation index](README.md)
