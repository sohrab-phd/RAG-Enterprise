# REGRESSION_MATRIX.md — RC3.7 / Version 1.0

Legend: **PASS** | **FAIL** | **NOT TESTED** | **PARTIAL**

| Subsystem / RC capability | Status | Evidence |
| --- | --- | --- |
| CQRS / application boundaries | PASS | No contract changes; suites green |
| Dependency injection container | PASS | App boots; `/ready` DI check OK |
| Domain model / enums | PASS | Knowledge/indexing/generation tests |
| API contracts (`/api/v1`) | PASS | API smoke 8/8 + route tests |
| Database schema / Alembic | PASS | App migrations + delete cascade tests |
| Knowledge base CRUD | PASS | `tests/knowledge` |
| Folder nested + recursive delete | PASS | `test_delete_folder.py` |
| Document upload / process / index | PASS | knowledge + indexing + E2E |
| Document / folder / KB cascade cleanup | PASS | delete_* cascade tests |
| Chunking | PASS | indexing/chunking tests |
| Persian normalization | PASS | processing tests + RC37 golden alignment |
| PDF extraction (RC3.3) | PASS | processing/parser tests + prior RC report |
| Embedding layer (BGE-M3 / deterministic) | PASS | indexing provider tests + `/ready` |
| Hybrid retrieval dense+BM25+RRF (RC3.5) | PASS | `test_hybrid_bm25.py` + Golestan Hit@1/MRR |
| Ranking RC3.2 | PASS | `test_ranking.py` + Golestan MRR 0.90 |
| Evidence selection RC3.6 | PASS | unit + live gold-in-selected 0.95 |
| Context assembly | PASS | generation context assembly tests |
| PromptBuilder / templates RC3.4 | PASS | prompt builder tests |
| GenerationService / abstain RC3.1 | PASS | generation service tests + chat smoke |
| Citations | PASS | citation tests + E2E |
| Chat conversations / history | PASS | generation persistence tests |
| Evaluation engine | PASS | evaluation tests + E2E eval hook |
| Ollama provider | PASS | `/ready` llm reachable; provider tests |
| Launcher `run.py` | PASS | code path review + docker/ready operational |
| Frontend architecture / Vitest | PASS | 15/15 |
| Frontend exhaustive manual UX | PARTIAL | Automated only in this gate |
| Concurrent write stress | PARTIAL | Covered by unit/integration patterns; no dedicated soak |
| RC2.1–RC2.11 feature set | PASS | Covered by knowledge/indexing/retrieval/gen suites + prior acceptance |
| RC3.1 False abstain | PASS | generation abstain tests |
| RC3.2 Ranking | PASS | ranking + Golestan |
| RC3.3 PDF extraction | PASS | prior report + parser tests |
| RC3.4 Persian generation prompts | PASS | prompt tests |
| RC3.5 Hybrid retrieval | PASS | hybrid tests + Golestan |
| RC3.6 Evidence selection | PASS | evidence tests + Golestan |
| Security / multi-tenant headers | PASS | scoped repository tests |
| Observability logs | PASS | structured logs observed in E2E/API |
