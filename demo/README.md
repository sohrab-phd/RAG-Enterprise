# Official Demo Workspace (Version 1)

> **Release candidate:** RC1.4  
> **Audience:** operators, reviewers, and public GitHub visitors  
> **Content:** synthetic Persian enterprise policies for شرکت نوین‌پرداز (NovinPardaz)  
> **Safe for public GitHub:** no real customers, secrets, or PII

This folder is the **official demonstration corpus** for RAG-enterprise Version 1.
Import these documents into a knowledge base, index them, ask the suggested questions
in Chat, then run Feature 007 evaluation against the golden set.

```text
demo/
  README.md                 ← you are here
  knowledge/                ← Persian policy documents (import these)
  questions/                ← suggested Chat questions
  evaluation/               ← Feature 007 golden dataset + manifest
```

## Company snapshot (consistent across documents)

| Fact | Value |
| --- | --- |
| Legal name | شرکت نوین‌پرداز |
| Annual leave (official staff) | ۲۰ روز کاری |
| Sick leave (per episode) | تا ۷ روز با گواهی پزشکی |
| Remote work cap | حداکثر ۲ روز در هفته |
| Core office days | شنبه تا چهارشنبه |
| Daily lodging ceiling (domestic) | ۴٬۵۰۰٬۰۰۰ ریال |
| Daily meal ceiling (domestic) | ۱٬۲۰۰٬۰۰۰ ریال |
| Policy owner | واحد منابع انسانی |

Documents **cross-reference** each other by title. Keep numbers unchanged when you
edit content so evaluation remain aligned.

## 1. Import demo documents

1. Start the backend and open the frontend Knowledge UI (see [docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md)).
2. Create a knowledge base, for example `نوین‌پرداز — سیاست‌های کارکنان`, with default language `fa`.
3. Activate the knowledge base (retrieval requires status `active`).
4. Upload **all four** files from `demo/knowledge/`:

| File | Title |
| --- | --- |
| `01-employee-handbook-fa.txt` | دفترچه راهنمای کارکنان |
| `02-leave-policy-fa.txt` | سیاست مرخصی |
| `03-remote-work-policy-fa.txt` | سیاست دورکاری |
| `04-travel-expense-policy-fa.txt` | سیاست هزینه سفر |

5. Use declared language `fa` and treat each file as one document.

## 2. Run indexing

After upload, advance each document version through processing → chunking →
embedding → indexing until `processing_status` is `indexed` (same pipeline as
RC1.3). Retrieval and Chat only see **indexed** content.

Confirm with retrieve smoke checks before Chat, for example:

- مرخصی استحقاقی سالانه چند روز است؟
- سقف اسکان روزانه در سفر داخلی چقدر است؟

## 3. Open Chat

1. Open the Chat route in the frontend.
2. Select the demo knowledge base.
3. Ask in Persian. Prefer grounded policy questions first; out-of-corpus prompts
   should abstain.

## 4. Suggested questions

Use the curated list in [`questions/suggested-questions-fa.md`](questions/suggested-questions-fa.md)
(~20 prompts). Topics cover handbook, leave, remote work, travel, and a few
deliberate abstention cases.

## 5. Run evaluation (Feature 007)

Golden records live under [`evaluation/`](evaluation/):

| Artifact | Role |
| --- | --- |
| `manifest.json` | Dataset identity / version / question count |
| `evaluation.jsonl` | One Feature 007 question record per line |

Feature 007’s loader expects a directory with **`manifest.json`** + **`dataset.jsonl`**.
Prepare a runnable dataset directory:

```bash
# from repository root
mkdir -p eval-artifacts/datasets/novinpardaz-v1
cp demo/evaluation/manifest.json eval-artifacts/datasets/novinpardaz-v1/
cp demo/evaluation/evaluation.jsonl eval-artifacts/datasets/novinpardaz-v1/dataset.jsonl
```

Then run an experiment with `EvaluationService` (see
[docs/backend/EVALUATION_FRAMEWORK.md](../docs/backend/EVALUATION_FRAMEWORK.md)):

- `dataset_id`: `novinpardaz-demo-fa`
- `dataset_version`: `1.0.0`
- `dataset_path`: path to the prepared directory
- `knowledge_base_id`: **your** activated demo KB id

### Citation IDs

`evaluation.jsonl` uses **stable synthetic UUIDs** for `knowledge_base_id`,
`document_id`, and `chunk_id` so the file validates offline and stays public.

Before scoring against a live index:

1. Replace `knowledge_base_id` on every row (and in `manifest.json`) with your KB id.
2. After indexing, replace each `chunk_id` / `document_id` with ids from your
   indexed corpus. Guidance is in each row’s `notes` field (`source_file` +
   `passage_contains`).

Rows tagged `abstain` keep empty citations and `expect_abstention: true`.

## Quality bar for this demo

- Realistic enterprise Persian (HR / finance language)
- Short documents with clear rules (not novels)
- Cross-linked policy titles
- Mix of easy / medium / hard questions plus abstentions
- Synthetic only — safe for public GitHub

## Related

- [Feature 007 — Golden Dataset](../specs/007-evaluation-framework/DATASET.md)
- [Evaluation Framework docs](../docs/backend/EVALUATION_FRAMEWORK.md)
- [E2E Happy Path (RC1.3)](../docs/backend/E2E_HAPPY_PATH.md)
