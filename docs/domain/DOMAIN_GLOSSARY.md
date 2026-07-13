# Domain Glossary

> **Status:** Accepted domain design.  
> **Purpose:** Canonical vocabulary for RAG-enterprise business and architecture discussions.

## A

### Abstention

A deliberate assistant outcome when evidence is insufficient, unauthorized, conflicting,
or blocked by policy. An abstained answer is preferable to an unsupported claim.

### ACL (Access Control List)

Resource-level access rules applied in addition to role permissions. Used for documents,
knowledge bases, conversations, and connectors.

### Agent

A workflow that may combine retrieval, generation, and tool invocation. In this platform,
agents are governed workflows, not autonomous unbounded actors.

### Aggregate

A cluster of domain objects treated as one consistency boundary. Example: `Document`
and its `DocumentVersion` history.

## C

### Catalog

Platform-maintained registry of providers, models, or tools that tenants may enable but
do not own.

### Chatbot

The first user-facing client of the platform. It consumes retrieval and generation
services but does not define the platform boundary.

### Chunk

The smallest stable retrieval unit derived from a `DocumentVersion`, with offsets,
language, and lineage metadata.

### Citation

A link from an assistant `Message` to a `Chunk` and its source document span used as
evidence in an answer.

### Classification Label

A data sensitivity marker such as `public_internal`, `restricted`, `confidential`, or
`regulated` that affects access, logging, and retention.

### Connector

See **IntegrationConnector**.

### Conversation

A workspace-scoped dialogue session that uses a pinned retrieval configuration, prompt
template, and LLM provider to consume knowledge.

## D

### Document

The logical identity of a knowledge asset regardless of how many versions or formats exist.

### Document Version

An immutable extracted snapshot of a document at a point in time, including processing
status and extraction method.

## E

### Embedding

A vector representation of a `Chunk` under a specific `EmbeddingModel`.

### Embedding Model

A registered embedding capability defined by provider, model key, dimensions, and lifecycle.

### Evaluation

A controlled measurement of retrieval or answer quality against acceptance thresholds.

### Evidence

Retrieved content used to support an answer, including chunks, citations, and future
ephemeral sources such as web search results.

## F

### Feedback

A user-submitted quality signal about a `Message` or `Citation`.

### Folder

A hierarchical container for organizing documents inside a knowledge base.

## K

### Knowledge Base

A curated corpus boundary with its own permissions, indexing policy, retrieval
configuration, and evaluation scope.

### Knowledge Platform

The full RAG-enterprise domain: tenancy, content, indexing, retrieval, AI configuration,
quality, and future integrations.

## L

### Locale

A language and regional formatting context used by users, conversations, prompts, and UI.

### LLM Provider

A registered generation provider and model defaults used for assistant responses.

## M

### MCP (Model Context Protocol)

A future external tool protocol integrated through `IntegrationConnector` and governed
`ToolDefinition` records.

### Membership

The assignment linking a `User` to an `Organization` and optionally a `Workspace` through
a `Role`.

### Message

A single turn in a `Conversation` from a user, assistant, system, or tool.

### Multitenancy

The isolation model where many customer organizations share platform infrastructure
without sharing business data.

## O

### Organization

The top-level tenant representing a customer company, including policy, billing, and
governance boundaries.

### Ownership

The authoritative aggregate root responsible for an entity's lifecycle and deletion
semantics.

## P

### Permission

A named authorization capability such as `document:read` or `tool:invoke`.

### Prompt Template

A versioned, locale-aware instruction artifact used for grounded generation and tool policy.

### Provenance

The traceable origin of content or evidence, including source document, version, chunk,
connector, and processing timestamps.

## R

### RAG (Retrieval-Augmented Generation)

A pattern where generation is informed by retrieved evidence from authorized knowledge.

### Retrieval Configuration

A versioned policy defining how a knowledge base is searched, filtered, ranked, and
assembled for generation.

### Role

A named bundle of permissions at organization or workspace scope.

## S

### SQL Agent

A future read-only query capability exposed through approved `ToolDefinition` records
connected to governed data sources.

### Superseded

A lifecycle state indicating a newer version or index generation replaces active use
while preserving historical lineage.

## T

### Tenant

Synonym for `Organization` in infrastructure and security discussions.

### ToolDefinition

An executable capability contract exposed by an integration connector, including schema
and approval policy.

## U

### User

A human platform identity that may belong to one or more organizations through memberships.

## W

### Web Search Augmentation

A future retrieval mode that supplements knowledge base evidence with ephemeral external
search results under connector policy.

### Workspace

An operational collaboration boundary within an organization for knowledge, conversations,
and integrations.

## Platform-specific acronyms

| Term | Meaning |
| --- | --- |
| ADR | Architecture Decision Record |
| ACL | Access Control List |
| KB | Knowledge Base |
| LLM | Large Language Model |
| MCP | Model Context Protocol |
| OCR | Optical Character Recognition |
| RAG | Retrieval-Augmented Generation |

## Related documents

- [Domain Model](DOMAIN_MODEL.md)
- [Bounded Contexts](BOUNDED_CONTEXTS.md)
- [Ownership Model](OWNERSHIP_MODEL.md)
- [Permission Model](PERMISSION_MODEL.md)
- [Multi-Tenancy](MULTI_TENANCY.md)
- [Entity Lifecycle](ENTITY_LIFECYCLE.md)
