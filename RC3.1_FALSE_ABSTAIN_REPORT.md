# RC3.1 — False Abstain Stabilization Report

> **Status:** Implemented (V1 stabilization)  
> **Scope:** Generation abstention decision logic, parser robustness, prompt instructions  
> **Non-goals:** Retrieval redesign, chunking, embeddings, CQRS/DI, APIs, frontend, schema

---

## 1. Executive summary

False abstains and malformed `ABSTAIN…` leaks were the largest Persian RAG UX
failures on curated FAQ/policy documents (notably سامانه گلستان).

**RC3.1 fixes the generation-side decision paths** so that:

- Raw `ABSTAIN…` text can never reach the end user.
- Users receive either a grounded answer with citations, or a clean Persian/English
  abstain explanation.
- Missing citation markers no longer force a false abstain when evidence already
  passed the sufficiency gate.
- Question-echo prefixes are stripped when a real answer follows.
- Prompt instructions explicitly forbid abstaining when evidence answers the question.

**Not fixed by RC3.1 (by design):** retrieval ranking wrong FAQ neighbors. That
remains a retrieval/chunking concern and is listed under remaining limitations.

---

## 2. Pipeline audit — every abstention path

```text
Question
  → strip / validate (empty → InvalidQuestionError, not abstain)
  → RetrievalService.retrieve()
  → evidence sufficiency gate          ← ABSTAIN path A
  → PromptBuilder (template v1)
  → LLMProvider.complete()
  → is_model_abstention(raw)           ← ABSTAIN path B
  → strip_question_echo + substance    ← ABSTAIN path C (echo-only)
  → validate_citations / salvage       ← ABSTAIN path D (salvage miss only)
  → Final GenerationResult
```

| Path | Trigger | Before RC3.1 | After RC3.1 |
| --- | --- | --- | --- |
| **A** | `result_count == 0` or `max_score < GENERATION_MIN_EVIDENCE_SCORE` | English abstain message; no LLM call | Localized FA/EN clean message; threshold unchanged at **0.25** |
| **B** | Model emits abstain token | Fragile regex `^ABSTAIN:\s*(\w+)\s*$` → miss → **completed leak** | Robust parser; always maps to clean abstain |
| **C** | Echo-only / empty after sanitize | Echo could pass with a marker | Echo-only → clean abstain (`empty_or_echo_answer`) |
| **D** | Answer with no valid `[n]` markers | Always `citation_validation_failed` abstain | **Salvage** top prompt chunk citation when answer is substantive |
| Failures | Retrieval / timeout / model errors | `FAILED` (unchanged) | Unchanged |

Code anchors:

- `generation/service.py` — orchestration
- `generation/citations.py` — parser, echo strip, salvage
- `generation/templates/v1.py` — system / output rules + `abstain_user_message()`

---

## 3. False-abstain failure classes (Golestan live eval baseline)

From the prior Golestan live eval (`n=20`, KB ABRU):

| Class | Count (approx.) | Root cause | RC3.1 impact |
| --- | --- | --- | --- |
| Retrieval mismatch | ~7 | Dense FAQ neighbor wrong; evidence not in top context | **Out of scope** (retrieval) |
| Parser leak | 2 | Malformed `ABSTAIN: …[n]` treated as completed | **Fixed** |
| Model false abstain | subset of 7 | Prompt allowed abstain despite evidence in context | **Mitigated** (prompt) |
| Echo / incomplete | 2 | Weak generation | **Mitigated** (prompt + echo strip) |
| Citation fail | possible | Answer without markers → abstain | **Fixed** (salvage) |

Baseline auto score: **8 pass / 2 partial / 10 fail**, **7 abstained**.

---

## 4. Code changes

### 4.1 Parser robustness (`citations.py`)

Accepts:

- `ABSTAIN`
- `ABSTAIN:`
- `ABSTAIN: insufficient_evidence`
- `ABSTAIN: insufficient_evidence [1]`
- `ABSTAIN : insufficient_evidence`
- Multiline `ABSTAIN:` + reason
- Trailing chunk junk / `[n]` markers

Rejects normal answers that merely contain the English word “abstain” in prose.

### 4.2 PromptBuilder instructions (`templates/v1.py`)

System rules now require:

- MUST answer when EVIDENCE contains the answer
- MUST NOT abstain in that case
- Never echo the question
- Persian answers for Persian questions
- Cite with `[n]`; invent nothing

### 4.3 Evidence confidence (`GENERATION_MIN_EVIDENCE_SCORE`)

| Setting | Value | Rationale |
| --- | --- | --- |
| Default | **0.25** | Kept. Golestan false abstains had top scores **0.50–0.73** — threshold was **not** the cause. |
| Deterministic / first-run | `0.0` | Already documented in `FIRST_RUN.md` (vectors are not semantic). |

Lowering the default toward 0.10–0.15 would admit weaker neighbors and risk
hallucinations without fixing FAQ ranking. **Decision: keep 0.25 for real BGE-M3.**

### 4.4 Generation service decision logic

1. Localized abstain via `v1.abstain_user_message(language)`.
2. Robust abstain detection before any user-facing answer.
3. Echo strip; echo-only → clean abstain.
4. Citation salvage when substantive answer lacks markers.
5. Append salvaged marker to answer text when missing.

---

## 5. Before / after metrics

### 5.1 Parser robustness (unit)

| Case | Before | After |
| --- | --- | --- |
| Canonical `ABSTAIN: insufficient_evidence` | Detected | Detected |
| `ABSTAIN: insufficient_evidence[n]…` | **Miss → leak** | Detected → clean FA/EN |
| `ABSTAIN: insufficient_evidence [3]` | **Miss → leak** | Detected |
| Normal answer with citations | Not abstain | Not abstain |

### 5.2 Generation decision (scripted LLM tests)

| Scenario | Before | After |
| --- | --- | --- |
| Malformed abstain + Persian Q | Completed with junk | Abstained, Persian clean copy, no `ABSTAIN`/`chunk_id` |
| Good FA answer, no markers | Abstained (`citation_validation_failed`) | Completed + salvaged `[1]` |
| Question echo + real answer | Echo kept | Echo stripped, answer kept |

### 5.3 Automated suite

```text
pytest tests/generation/test_citations.py \
       tests/generation/test_service.py \
       tests/generation/test_prompt_builder.py \
       tests/generation/test_api.py
→ all passed
```

---

## 6. Benchmark / regression artifacts

| Artifact | Purpose |
| --- | --- |
| `demo/evaluation/rc31_false_abstain_regression.jsonl` | Curated FA cases (leave/handbook/remote/travel + Golestan FAQ + true abstain) |
| Existing `demo/evaluation/evaluation.jsonl` | Unchanged baseline Persian policies |
| Unit/service tests above | Deterministic gates for parser / salvage / prompt / leak |

**How to run curated binding** (when demo or Golestan docs are indexed):

```bash
cd backend
uv run python -m tools.persian_rag_benchmark \
  --curated-dataset ../demo/evaluation/rc31_false_abstain_regression.jsonl \
  ...
```

(Use the project’s existing benchmark CLI flags from `tools/persian_rag_benchmark/README.md`.)

Acceptance intent for curated **in-corpus** rows with evidence in the prompt:

- False abstain rate → **approach zero** on generation-side classes (B/C/D).
- Malformed `ABSTAIN…` user responses → **impossible**.
- True out-of-corpus abstain → clean Persian message only.

---

## 7. Regression tests added

- `tests/generation/test_citations.py` — fragile abstain variants, echo strip, salvage, FA message
- `tests/generation/test_service.py` — leak prevention, citation salvage, echo strip E2E through `GenerationService`
- `tests/generation/test_prompt_builder.py` — anti-false-abstain prompt clauses

All prior generation tests remain green.

---

## 8. Remaining limitations

1. **Retrieval false neighbors** — If the correct FAQ pair is not in the assembled
   context, the model may still abstain. Fix requires hybrid retrieval / FAQ-sized
   chunks (future RC), not generation-only.
2. **Echo-only replies** — If the model returns only the question (no answer prose),
   RC3.1 returns a clean abstain rather than inventing facts. Prompt pressure reduces
   frequency; full elimination needs stronger local models or constrained decoding.
3. **OCR / digit corruption** — Bad extracted text (e.g. `02` vs `20`) can make a
   “correct” corpus answer factually wrong even when generation succeeds.
4. **Threshold 0.25** — Appropriate for BGE-M3; still set `0.0` for deterministic
   embedding demos.

---

## 9. Manual verification checklist

1. Ask a Persian leave-policy question with indexed handbook → grounded answer + `[n]`.
2. Force a scripted/malformed model abstain (or reproduce Golestan username Q) →
   **no** raw `ABSTAIN` / `chunk_id` in UI; Persian clean message if abstaining.
3. Ask an out-of-corpus question → clean abstain (FA).
4. Confirm `GENERATION_MIN_EVIDENCE_SCORE=0.25` with real embeddings; do not lower
   blindly.
5. Re-run generation unit tests after any prompt tweak.

---

## 10. Files touched

| File | Change |
| --- | --- |
| `backend/src/rag_enterprise/generation/citations.py` | Robust abstain parser, echo strip, salvage |
| `backend/src/rag_enterprise/generation/templates/v1.py` | Anti-false-abstain instructions + FA message |
| `backend/src/rag_enterprise/generation/service.py` | Decision logic wiring |
| `backend/tests/generation/test_*.py` | Regression coverage |
| `demo/evaluation/rc31_false_abstain_regression.jsonl` | Curated FA regression set |
| `docs/backend/RAG_GENERATION.md` | Abstention policy note |
| `RC3.1_FALSE_ABSTAIN_REPORT.md` | This report |
