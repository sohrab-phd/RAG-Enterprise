# RC3.3 — Persian PDF Extraction Quality Report

Status: implemented and live-reindexed for the uploaded 21-page Golestan PDF.

Scope: PDF text-layer extraction only. Retrieval, ranking, generation, embeddings,
chunking, APIs, CQRS/DI, schema, launcher, Docker, and provider code were not changed.

## 1. Files modified

- `backend/src/rag_enterprise/processing/parsers/pdf.py`
  - Persian-aware strategy selection, logical span reconstruction, layout ordering,
    wrapped-line joining, recurring margin removal, PDF-only cleanup, and diagnostics.
- `backend/tests/processing/test_pdf_parser.py`
  - Persian text, digit order, mixed Latin/Persian, FAQ boundaries, wrapped answers,
    two-column order, repeated headers/footers, punctuation, and English regression.
- `backend/tools/pdf_extraction_diagnostics.py`
  - Content-safe extraction diagnostics. It stores metrics and a document hash, not
    extracted document text.
- `backend/tools/rc33_golestan_eval.py`
  - Fixed 20-question live before/after retrieval and generation evaluation.
- `RC3.3_PDF_EXTRACTION_REPORT.md`
  - This report.

Local evaluation artifacts:

- `eval-artifacts/rc33-pdf-extraction.json`
- `eval-artifacts/rc33-golestan-before.json`
- `eval-artifacts/rc33-golestan-after.json`

## 2. Extraction pipeline

```text
PDF
  |
  +-- open + encryption validation
  |
  +-- per-page rawdict inspection
        |
        +-- no Arabic script -> PyMuPDF text mode, sort=True
        |
        +-- Arabic script
              |
              +-- preserve PyMuPDF logical character order inside each span
              +-- cluster fragmented spans into visual rows by glyph geometry
              +-- order Persian rows/spans RTL and non-Persian rows LTR
              +-- conservative RTL two-column block ordering
              +-- join only geometry-confirmed wrapped lines
              +-- preserve questions, answers, lists, headings, punctuation
  |
  +-- NFKC compatibility-form normalization
  +-- deterministic PDF-only artifact and RTL punctuation cleanup
  +-- remove recurring page-margin headers/footers
  +-- existing shared Persian normalization
  +-- existing chunk/index pipeline (unchanged)
```

The critical design rule is: geometry orders spans, rows, blocks, and columns, but
does not reorder characters inside a PyMuPDF span. The old implementation sorted
every character by X coordinate. That correctly helped some Persian fragments but
reversed numbers, URLs, and English phrases.

## 3. PyMuPDF mode investigation

The uploaded Golestan PDF has 21 pages and 458 text blocks. The diagnostics exercised:

- `text` default: 13,775 extracted characters.
- `text`, `sort=True`: 30,453 characters; this PDF produced duplicated/reordered
  material, so it was not safe as the Persian strategy.
- `blocks`, `sort=True`: 458 blocks.
- `words`, `sort=True`: 2,801 words.
- `dict`: 458 blocks; useful for span metadata but not individual glyph provenance.
- `rawdict`: 458 blocks; selected for Persian because it retains logical span order
  and glyph coordinates.

Only one real Persian PDF was present in local storage. Its 21 pages were inspected,
and deterministic synthetic rawdict fixtures cover mixed-script lines, two columns,
FAQ layout, wrapped paragraphs, headers/footers, and punctuation. Claims about
unseen scanned/OCR PDF families are intentionally not made.

## 4. Before/after extraction examples

Digit order:

```text
Before: کارشناسی: 02 واحد ... سقف 42 واحد
After:  کارشناسی: 20 واحد ... سقف 24 واحد

Before: کارشناسی ارشد: 41 واحد
After:  کارشناسی ارشد: 14 واحد

Before: 01 تا 51 دقیقه ... بیشتر از 03 دقیقه
After:  10 تا 15 دقیقه ... بیشتر از 30 دقیقه
```

Mixed Latin/Persian:

```text
Before: "ri.ca.urba.natselog"
After:  "golestan.abru.ac.ir"

Before: هدش زورهب Google Chrome ای Firefox لوا معم
After:  معمولا Firefox یا Google Chrome بهروز شده
```

Known glyph-order artifact:

```text
Before: اطالعات
After:  اطلاعات
```

`اطالعات` is repaired only as an exact Arabic-script token with Unicode letter
boundaries. There is no fuzzy dictionary correction. Unknown words and unknown
numbers are never guessed.

## 5. Extraction quality metrics

Persisted pre-RC3.3 extraction versus the new extraction:

- Numeric tokens: 23 versus 23 (none lost).
- Numeric order mismatches against PyMuPDF logical spans: 13 -> 0.
- Known `اطالعات` artifacts: 11 -> 0.
- Correct `اطلاعات` tokens: 0 -> 12.
- Valid Golestan URL: absent -> present.
- Replacement characters (`U+FFFD`): 0 -> 0.
- Arabic `ي` / `ك` variants after normalization: 0 -> 0.
- FAQ question lines preserved: 107 -> 107.
- Total lines: 661 -> 653.
- Blank separator lines: 330 -> 326.
- Repeated Golestan margin lines removed: 0 (none met the conservative recurrence
  rule); dedicated tests verify removal for repeated headers and page-number footers.
- Tracked character/number corruption count: 25 -> 0
  (13 digit-order mismatches + 11 known glyph artifacts + 1 reversed URL).

Diagnostics persisted with the indexed version:

```text
pdf_arabic_pages:21
pdf_geometry_pages:21
pdf_fallback_pages:0
pdf_repeated_margin_lines_removed:0
pdf_replacement_characters:0
pdf_presentation_form_characters:0
pdf_deterministic_repairs:12
```

## 6. Re-index and 20-question benchmark

The uploaded Golestan document was uploaded as a new version and processed through
the normal public workflow. Result: 13 chunks and 13 embeddings indexed.

Deterministic retrieval metrics improved:

- Hit@1: 0.7000 -> 0.8500.
- MRR: 0.7500 -> 0.8917.

Live Qwen 2.5 7B answer metrics from one run per index:

- Pass: 6/20 -> 6/20.
- Pass rate: 30% -> 30%.
- Abstains: 11 -> 13.
- Wrong answers: 3 -> 1.
- Average request latency: 4,215 ms -> 3,682 ms.

Interpretation: extraction materially improved the indexed evidence and deterministic
retrieval ranking. It did not improve the single-run generation pass rate. Two wrong
answers became abstentions, while one previously passing response abstained in the
second probabilistic model run. Changing generation or abstention policy is explicitly
outside RC3.3, so these results are reported rather than masked or tuned around.

Concrete retrieval recoveries include:

- Login URL: not found in top 8 -> rank 1.
- `اطلاعات جامع`: not found in top 8 -> rank 1.
- `20 واحد`: not found in top 8 -> rank 3.
- Emergency-drop answer: rank 2 -> rank 1.

## 7. Performance impact

- New extraction time for the 21-page Golestan PDF: 165.59 ms in the stored
  diagnostic run, about 7.9 ms/page.
- Extraction is local CPU work only.
- No new dependency, model inference, network call, or secondary OCR pass.
- Re-index produced the same 13 chunk/embedding count, so downstream cardinality did
  not increase.

## 8. Verification

Scoped gates:

```text
17 processing/PDF tests passed
ruff check: passed for all RC3.3 files
ruff format --check: passed for all RC3.3 files
mypy: passed for the production PDF parser
```

The full backend suite reached completion with one unrelated existing failure:
`tests/e2e/test_rag_happy_path.py::test_rag_happy_path_persian_leave_policy`.
That fixture uploads `text/plain`, so the PDF parser is not on its execution path.
One PostgreSQL integration test was skipped by its existing opt-in guard.

Repository-wide Ruff and MyPy also report pre-existing errors in untouched health,
repository, provider, and RC3.2 files. The changed RC3.3 files pass their scoped
quality gates.

## 9. Remaining limitations

1. Image-only/scanned PDFs still require OCR; this RC repairs text layers only.
2. A corrupted text layer with no reliable logical span order cannot be repaired
   without guessing. The parser preserves it and emits diagnostics.
3. The exact `اطالعات` repair is intentionally narrow. No general spell checker or
   language-model correction is used.
4. Complex tables with merged cells and irregular floating text can remain
   ambiguous. Two-column ordering activates only when both columns pass conservative
   geometry checks.
5. Repeated headers/footers are removed only when the same normalized margin line
   appears on at least 60% of pages (minimum two), preventing aggressive body deletion.
6. Only one real Persian PDF was locally available. Additional representative,
   approved, non-sensitive Persian PDF fixtures should be added before claiming broad
   coverage across publishers and font encodings.
7. Live generation remains model-dependent. Retrieval improved, but the 20-question
   pass rate remains 30%; addressing those abstentions belongs to generation policy,
   not extraction.
