# AI Engineering Rules

## Platform principles

- AI output is probabilistic and untrusted. Deterministic application code owns
  identity, authorization, data access, policy, validation, and side effects.
- No RAG, model, embedding, or LangGraph feature is implemented without an approved
  specification defining quality, safety, latency, cost, observability, and fallback.
- Hide providers behind narrow injected interfaces; domain/application code must not
  depend directly on provider SDK types.
- Every AI path supports timeouts, cancellation, bounded retries, rate limits, and
  explicit degraded behavior.

## Models, prompts, and configuration

- Pin model identifiers and material inference parameters by environment. Never
  rely on mutable provider aliases in production.
- Version prompts as reviewed repository artifacts or versioned configuration;
  prompts are code and require tests, ownership, and change history.
- Separate system policy, application instructions, retrieved context, tool output,
  and user input with explicit delimiters and trust labels.
- Keep secrets and tenant policy out of prompts unless strictly required and
  approved. Minimize data sent to providers.
- Record provider, model, prompt version, token usage, latency, retry count, and
  outcome without logging sensitive content.

## Retrieval

- Preserve source identity, tenant scope, ACL metadata, document version, chunk
  offsets, and ingestion lineage through indexing and retrieval.
- Enforce tenant and authorization filters before semantic ranking; never ask the
  model to filter unauthorized context.
- Chunking, embedding, index, retrieval, and reranking versions are explicit and
  reproducible. Re-indexing has a migration and rollback plan.
- Require citations that map generated claims to retrieved source spans when the
  product contract calls for grounded answers.
- Define behavior for insufficient, conflicting, stale, or unauthorized evidence;
  abstention is preferable to unsupported claims.

## LangGraph and tools

- Graph nodes have typed state, one responsibility, deterministic routing where
  possible, idempotent side effects, and explicit retry/error transitions.
- Persist only the minimum checkpoint state with retention and tenant controls.
- Tool schemas are narrow and validated. Use allowlists, least privilege, execution
  timeouts, result-size limits, and audit logs.
- Human approval is required before destructive, financial, privileged, external
  communication, or otherwise irreversible actions.
- Never grant the model raw database, shell, filesystem, or unrestricted network
  access.

## Safety and security

- Treat documents, retrieval results, web content, user messages, and tool output as
  potentially malicious prompt-injection content.
- Enforce policy outside the model and validate model-produced structured data
  before use.
- Test cross-tenant leakage, indirect prompt injection, data exfiltration, unsafe
  tool use, denial-of-wallet, and oversized-context scenarios.
- Apply data classification, consent, retention, deletion, and residency rules to
  prompts, embeddings, traces, caches, checkpoints, and evaluation datasets.

## Evaluation and release

- Maintain representative, versioned datasets with provenance and no uncontrolled
  production data.
- Measure retrieval recall/precision, groundedness, citation fidelity, answer
  relevance, safety, latency percentiles, availability, and cost per request.
- Define acceptance thresholds before implementation; compare candidates against a
  pinned baseline and retain evaluation artifacts.
- Use staged rollout, feature flags, budgets, kill switches, and rollback for
  production AI changes. Provider-dependent evaluation is never the only test gate.
