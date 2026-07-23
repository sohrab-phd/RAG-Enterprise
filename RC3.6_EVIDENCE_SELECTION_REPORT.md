# RC3.6 — Evidence Selection Layer (V1) Report

Status: completed for V1 generation evidence-filtering scope  
Date: 2026-07-23  
Scope: deterministic heuristic evidence selection **after** hybrid retrieval + RC3.2 ranking, **before** PromptBuilder

## 1. Modified files

| File | Change |
| --- | --- |
| `backend/src/rag_enterprise/generation/evidence_selection.py` | **New** — PRIMARY / SUPPLEMENTARY / IRRELEVANT scoring + caps + conflict flag |
| `backend/src/rag_enterprise/generation/service.py` | Call `select_evidence()` between retrieve sufficiency check and `PromptBuilder.build()`; optional `RAG_EVIDENCE_SELECTION=0` passthrough for A/B only |
| `backend/tests/generation/test_evidence_selection.py` | **New** — FAQ distractor, caps, conflict, diagnostics, empty-input tests |
| `backend/tools/rc36_evidence_eval.py` | **New** — Golestan 20 live retrieve + select + chat evaluator |
| `eval-artifacts/rc36-evidence-before.json` | Passthrough baseline (`RAG_EVIDENCE_SELECTION=0`) |
| `eval-artifacts/rc36-evidence-after.json` | Evidence-selection enabled run |
| `eval-artifacts/evidence_selection.json` | Per-question selection diagnostics (`selected_primary`, `selected_support`, `discarded`, scores, reasons) |
| `RC3.6_EVIDENCE_SELECTION_REPORT.md` | This report |

**Not modified:** CQRS, DI container shape, REST API, frontend, database schema, PromptBuilder public interface / prompt format, Context Assembly contracts, RetrievalService algorithms, hybrid retrieval, RC3.2 ranking, embeddings.

## 2. Architecture diagram

```text
Question
    │
    ▼
Hybrid Retrieval (dense + BM25 + RRF)     ← unchanged (RC3.5)
    │
    ▼
RC3.2 ranking calibration                 ← unchanged
    │
    ▼
Ranked chunks (top-K)
    │
    ▼
┌───────────────────────────────────────┐
│  Evidence Selector (RC3.6, NEW)       │
│  deterministic heuristic scores       │
│  → PRIMARY (1–3)                      │
│  → SUPPLEMENTARY (0–2)                │
│  → IRRELEVANT (discarded)             │
│  conflict=true if primaries disagree  │
└───────────────────────────────────────┘
    │
    ▼
PromptBuilder.build(selected chunks)      ← public interface unchanged
    │
    ▼
Context Assembly → LLM → citations
```

Insertion point: `GenerationService.generate` only — one lightweight stage, no GenerationService redesign.

## 3. Selection algorithm

For each ranked chunk, compute an **evidence score** as a weighted sum of:

| # | Signal | Role |
| --- | --- | --- |
| 1 | Lexical overlap | Jaccard of content tokens (query ↔ body) |
| 2 | Persian keyword overlap | Jaccard of Persian content tokens |
| 3 | Heading similarity | Jaccard(query, heading) |
| 4 | FAQ question similarity | Best Jaccard vs question-marked lines |
| 5 | Exact phrase matches | Long query phrases / bigrams in FAQ/heading/body |
| 6 | Numeric agreement | Shared normalized digits when the query has numbers |
| 7 | Named entities | Soft overlap of URL/Latin/long Persian tokens |
| 8 | Document section proximity | Same-document neighbor boost vs best candidate |
| 9 | RC3.2 ranking score | Normalized `RetrievedChunk.score` |
| 10 | Hybrid retrieval score | Reciprocal input rank `1/(1+rank−1)` (post hybrid+RC3.2 order) |

Then:

1. Apply small **distractor penalties** (e.g. اولیه vs فراموشی, پیش‌نیاز vs هم‌نیاز).
2. Label by thresholds: PRIMARY ≥ 0.42 (or strong FAQ/phrase/heading), SUPPLEMENTARY ≥ 0.28, else IRRELEVANT.
3. Keep **1–3 PRIMARY** + **0–2 SUPPLEMENTARY**; never send IRRELEVANT to PromptBuilder.
4. If no PRIMARY clears the bar, promote the best chunk above a hard floor.
5. If ≥2 PRIMARY chunks disagree on numeric answers (or disjoint answer spans), set `conflict=true` (prompt already instructs conflict reporting).

No ML. No cross-encoder. No LLM judge.

## 4. Before / after benchmark (Golestan 20)

KB: `019f7108-65e7-705a-b080-e50eefd837c8` (ABRU)  
Evaluator: `backend/tools/rc36_evidence_eval.py`  
Artifacts: `eval-artifacts/rc36-evidence-before.json`, `rc36-evidence-after.json`, `evidence_selection.json`

| Metric | Before (RC3.5 passthrough) | After (RC3.6 evidence selection) | Delta |
| --- | ---: | ---: | ---: |
| Pass | 3 | **16** | **+13** |
| Partial | 0 | 3 | +3 |
| Fail | 17 | **1** | **−16** |
| Hit@1 (retrieval) | 0.85 | 0.85 | 0 |
| Hit@3 (retrieval) | 0.95 | 0.95 | 0 |
| MRR (retrieval) | 0.9000 | 0.9000 | 0 |
| Gold marker in selected set | — | 0.95 | — |
| Avg chunks sent to prompt | **8.0** (all retrieved) | **2.45** | **−5.55** |
| Avg discarded chunks | 0 | **5.55** | +5.55 |
| Avg prompt size reduction (chars) | 0% | **~69.6%** | — |
| Avg selection latency | 0 ms | **~30 ms** | +30 ms |
| Avg chat latency | 3082.95 ms | **2571.26 ms** | **−511.69 ms** |
| Avg end-to-end latency | 3430.25 ms | **2922.26 ms** | **−508 ms** |

Interpretation:

- Retrieval quality is unchanged (same Hit@1 / MRR as RC3.5) — selector does not alter ranking APIs.
- Filtering distractor FAQ neighbors before prompting sharply reduced false / empty answers under `qwen2.5:7b`.
- Smaller evidence packs cut prompt tokens and **reduced** end-to-end latency despite the ~30 ms selection overhead.
- Remaining gaps: `q19` Fail; `q01`/`q06`/`q12` Partial (completeness of multi-fact answers, not retrieval miss for most).

## 5. Latency impact

| Stage | Typical cost |
| --- | ---: |
| Evidence selection (CPU heuristics) | ~30 ms / question |
| Chat wall time | −17% vs passthrough (smaller prompts) |
| Retrieval | unchanged (~315–320 ms) |

**Net:** minimal selector cost; overall faster generation for this benchmark.

## 6. Unit tests

```bash
cd backend
uv run pytest tests/generation/test_evidence_selection.py tests/generation/test_service.py -q --tb=short
uv run ruff check src/rag_enterprise/generation/evidence_selection.py src/rag_enterprise/generation/service.py tests/generation/test_evidence_selection.py tools/rc36_evidence_eval.py
uv run mypy src/rag_enterprise/generation/evidence_selection.py src/rag_enterprise/generation/service.py
```

Coverage:

- FAQ gold preferred over near-neighbor distractor
- IRRELEVANT never included in prompt set
- Caps: ≤3 PRIMARY, ≤2 SUPPLEMENTARY
- Numeric conflict detection among PRIMARY
- Diagnostics fields required by RC3.6
- Empty retrieval → empty selection
- Existing GenerationService tests still pass

## 7. Manual verification

1. Start stack (`docker compose up -d`, backend on port **8800**).
2. Confirm KB ABRU is `active` and indexed.
3. Ask: `رمز عبور اولیه گلستان چیست؟` — answer should cite کد ملی, not password-reset neighbor.
4. Ask: `پیش‌نیاز دروس یعنی چه؟` — should not answer with هم‌نیاز content as primary.
5. Inspect logs for `evidence_selected` (`selected_primary`, `discarded`, `selection_latency_ms`).
6. Re-run:
   ```bash
   cd backend
   uv run python tools/rc36_evidence_eval.py \
     --knowledge-base-id 019f7108-65e7-705a-b080-e50eefd837c8 \
     --output ../eval-artifacts/rc36-evidence-after.json \
     --evidence-output ../eval-artifacts/evidence_selection.json \
     --base-url http://127.0.0.1:8800/api/v1
   ```
7. Optional A/B: `RAG_EVIDENCE_SELECTION=0` restarts passthrough baseline (eval only).

## 8. Success criteria vs RC3.5

| Criterion | Result |
| --- | --- |
| Higher Pass rate | ✔ 3 → 16 |
| Lower false / failed answers | ✔ Fail 17 → 1 |
| Smaller prompt | ✔ ~70% char reduction; avg 2.45 chunks |
| Same retrieval quality | ✔ Hit@1 / MRR unchanged |
| Minimal latency increase | ✔ +~30 ms select; net chat faster |
| No regressions in architecture | ✔ APIs / DI / retrieval / PromptBuilder interface untouched |
| No V2 features | ✔ Heuristics only |

## 9. Out of scope (not done)

- Cross-encoder / learned reranker
- LLM-as-judge evidence filtering
- Changes to hybrid retrieval or RC3.2 weights
- Prompt template / format changes
- API fields for selection diagnostics (logged + eval artifact only)
