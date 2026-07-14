# Evaluation fixture map (RC1.4)

Synthetic UUIDs used in `evaluation.jsonl` / `manifest.json` before live binding:

| Role | UUID | Source file |
| --- | --- | --- |
| Knowledge base (placeholder) | `018f0000-0000-7000-8000-00000000kb01` | — |
| Handbook document | `…d001` | `knowledge/01-employee-handbook-fa.txt` |
| Handbook chunk (placeholder) | `…c001` | same |
| Leave document | `…d002` | `knowledge/02-leave-policy-fa.txt` |
| Leave chunk (placeholder) | `…c002` | same |
| Remote document | `…d003` | `knowledge/03-remote-work-policy-fa.txt` |
| Remote chunk (placeholder) | `…c003` | same |
| Travel document | `…d004` | `knowledge/04-travel-expense-policy-fa.txt` |
| Travel chunk (placeholder) | `…c004` | same |

Replace placeholders with ids from your indexed knowledge base before measuring
Recall@K / citation metrics. See the parent [README](../README.md).
