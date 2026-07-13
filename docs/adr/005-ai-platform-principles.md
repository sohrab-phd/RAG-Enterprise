# ADR-005: AI Platform Principles

**Status:** Accepted  
**Date:** 2026-07-13

## Context

RAG-enterprise will eventually process untrusted documents and user input, retrieve
tenant-scoped evidence, call probabilistic model providers, and potentially execute
tools. Model behavior, provider APIs, costs, and quality change over time. Enterprise
use requires reproducibility, authorization, auditability, safe failure, measurable
quality, and provider portability rather than prompt-only controls.

## Decision

Govern future AI capabilities by these principles:

- Deterministic code owns identity, authorization, tenant isolation, policy, tool
  permissions, validation, and irreversible side effects.
- Providers are accessed through injected interfaces; model IDs, prompts, inference
  settings, embeddings, indexes, graph versions, and evaluation datasets are versioned.
- Retrieved content and tool output are untrusted data, not instructions.
- Authorization and tenant filters execute before retrieval and ranking.
- Evidence lineage and citations are preserved; insufficient evidence produces an
  explicit abstention or degraded result.
- Every AI path has quality, safety, latency, availability, and cost acceptance
  criteria plus timeout, budget, fallback, kill switch, staged rollout, and rollback.
- LangGraph nodes use typed state, bounded execution, least-privilege tools, and human
  approval for destructive, privileged, financial, or external communication actions.
- Evaluation precedes release and compares against a pinned baseline.
- Sensitive prompt/document content is not logged by default and inherits source
  classification, retention, deletion, and residency requirements.

## Alternatives considered

### Direct provider SDK usage throughout application code

Speeds initial integration but creates vendor lock-in, leaked SDK types, duplicated
resilience logic, and poor testability.

### Prompt-only safety and authorization

Is easy to prototype but probabilistic, vulnerable to direct and indirect injection,
and unsuitable for enforcing enterprise policy.

### Autonomous agents with broad tools

Can increase task breadth, but creates unacceptable privilege, audit, and irreversible
side-effect risk without narrow tools and deterministic approval controls.

### Online metrics without offline evaluation

Captures production behavior but makes regressions difficult to detect before exposure
and can involve sensitive data.

## Consequences

- AI features require more specification, evaluation, versioning, and telemetry before
  release.
- Provider replacement and controlled experimentation remain feasible.
- Some requests will abstain or degrade rather than produce an unsupported answer.
- Human approval may add latency to high-impact workflows.
- Evaluation assets and traces become governed data products with owners and retention.
- No RAG or agent implementation is authorized by this ADR alone; each capability still
  requires an approved feature specification.
