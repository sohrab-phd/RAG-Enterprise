# PERFORMANCE_REPORT.md — RC3.7

Scope: measure only — no optimization.

Environment: Windows host, Docker Postgres/Redis healthy, backend `:8800`, Ollama `qwen2.5:7b`, embeddings `BAAI/bge-m3` (sentence_transformers), KB ABRU Golestan.

## Startup

| Signal | Observation |
| --- | --- |
| Docker compose Postgres/Redis | Healthy on ports 5433 / 6379 |
| Backend `/api/v1/live` | 200 |
| Backend `/api/v1/ready` | 200; LLM probe ~8–10 s; embedding index aligned |
| Cold `/ready` cost | Dominated by Ollama tags/version probe (readiness, not per-chat) |

## Upload / Processing / Embedding

| Stage | Observation |
| --- | --- |
| Upload + version + process (E2E mock/deterministic) | Process path ~90–200 ms in local ASGI E2E (tiny fixture) |
| Live production indexing | Not soak-tested in RC3.7; existing indexing tests + ABRU corpus already indexed |
| Embedding model | BGE-M3 dims 1024; `/ready` sample_cosine ≈ 1.0 vs indexed vectors |

## Retrieval

| Metric | Value |
| --- | ---: |
| Avg retrieval latency (Golestan 20) | 471.03 ms |
| Hit@1 | 0.85 |
| Hit@3 | 0.95 |
| MRR | 0.90 |

Unchanged vs RC3.5/RC3.6 retrieval quality.

## Evidence Selection

| Metric | Value |
| --- | ---: |
| Avg selection latency | 38.62 ms |
| Avg selected chunks | 2.45 |
| Avg discarded chunks | 5.55 |
| Avg prompt char reduction | 69.57% |
| Gold marker retained in selected set | 0.95 |

## Generation

| Metric | Value |
| --- | ---: |
| Avg chat latency | 3021.57 ms |
| Avg end-to-end (retrieve+select+chat path timing in eval) | 3532.74 ms |
| Golestan Pass / Partial / Fail | 14 / 5 / 1 |

## Prompt / Context Size

| Metric | Value |
| --- | ---: |
| Pre-selection context | top_k=8 retrieved chunks |
| Post-selection context | ~2.45 chunks average |
| Reduction | ~70% character estimate |

## Memory / CPU / VRAM

| Metric | Status |
| --- | --- |
| Process RSS / CPU % | NOT INSTRUMENTED in-process this gate |
| GPU VRAM (Ollama / ST) | NOT INSTRUMENTED; Ollama + local ST share host GPU/CPU as configured |
| Bottleneck (qualitative) | Generation (LLM) ≫ retrieval ≫ evidence selection |

## Index Size

| Metric | Status |
| --- | --- |
| pgvector embedding rows for ABRU | Present (active KB); exact row count not required for release gate |
| Lexical side-file | Optional under `FILE_STORAGE_ROOT/.lexical/` (RC3.5) |

## Bottlenecks (identify only)

1. **LLM generation** (~3 s/question) — primary latency.
2. **Dense+hybrid retrieval** (~0.5 s) — secondary.
3. **Evidence selection** (~40 ms) — negligible vs generation.
4. **Readiness LLM probe** (~10 s) — startup/ops only.
