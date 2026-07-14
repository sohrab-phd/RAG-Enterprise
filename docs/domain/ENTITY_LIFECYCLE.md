# Entity Lifecycle

> **Status:** Accepted domain design.  
> **Purpose:** Define lifecycle states, transitions, and invariants for core entities.

## 1. Lifecycle conventions

| Convention | Rule |
| --- | --- |
| Terminal states | `deleted`, `retired`, and `decommissioned` are terminal for active use. |
| Supersession | New versions supersede old ones; historical records remain for audit and citation. |
| Authorization | State transitions that expose data require permission checks before entry. |
| Idempotency | Repeated transition requests must not create duplicate active versions. |
| Audit | Security, deletion, and AI configuration transitions emit audit events. |

## 2. Tenant entities

### Organization

```mermaid
stateDiagram-v2
    [*] --> provisioning
    provisioning --> active: policy_ready
    active --> suspended: billing_or_policy_violation
    suspended --> active: restored
    active --> decommissioned: contract_end
    suspended --> decommissioned: contract_end
    decommissioned --> [*]
```

| State | Meaning | Allowed operations |
| --- | --- | --- |
| `provisioning` | Tenant created; baseline policy incomplete | Configure org settings only |
| `active` | Fully operational | All approved operations |
| `suspended` | Access restricted | Read-only or admin-only per policy |
| `decommissioned` | Tenant wind-down complete | Export and audit only |

**Invariants:** At least one active workspace admin pathway must exist before leaving `provisioning`.

---

### Workspace

```mermaid
stateDiagram-v2
    [*] --> active
    active --> archived: admin_archive
    archived --> active: admin_restore
    archived --> deleted: retention_elapsed
    deleted --> [*]
```

| State | Meaning |
| --- | --- |
| `active` | Normal operations |
| `archived` | No new ingestion or conversations; read and audit allowed |
| `deleted` | Logical deletion after retention window |

---

### User

```mermaid
stateDiagram-v2
    [*] --> invited
    invited --> active: accept_invite
    active --> disabled: admin_disable
    disabled --> active: admin_enable
    active --> deleted: gdpr_or_admin_delete
    disabled --> deleted: gdpr_or_admin_delete
    deleted --> [*]
```

---

### Membership

```mermaid
stateDiagram-v2
    [*] --> pending
    pending --> active: approved_or_auto
    active --> revoked: admin_revoke
    revoked --> [*]
```

## 3. Knowledge entities

### Knowledge Base

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> active: publish
    active --> reindexing: model_or_policy_change
    reindexing --> active: reindex_complete
    active --> archived: admin_archive
    archived --> active: admin_restore
    archived --> deleted: retention_elapsed
    deleted --> [*]
```

**Operator lifecycle (RC1.6):** `draft` → **Publish** → `active` → **Archive** → `archived` → **Restore** → `active`.

**Transition notes:**

- `POST .../knowledge-bases/{id}/publish` is the only draft → active transition (empty KB allowed).
- Entering `reindexing` does not delete existing chunks; new embeddings may be built in parallel.
- Conversations may continue during `reindexing` using the last active retrieval configuration unless policy blocks it.
- Retrieval behavior is unchanged: only `active` knowledge bases are searchable.

---

### Document

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> active: first_version_indexed
    active --> archived: owner_archive
    archived --> active: owner_restore
    active --> deleted: delete_authorized
    archived --> deleted: delete_authorized
    deleted --> [*]
```

**Invariant:** A `deleted` document retains historical versions and citations for audit unless legal deletion applies.

---

### Document Version

```mermaid
stateDiagram-v2
    [*] --> uploaded
    uploaded --> extracting: extraction_started
    extracting --> extracted: extraction_succeeded
    extracting --> failed: extraction_failed
    extracted --> chunking: chunking_started
    chunking --> chunked: chunking_succeeded
    chunking --> failed: chunking_failed
    chunked --> indexing: embedding_started
    indexing --> indexed: embeddings_indexed
    indexing --> failed: indexing_failed
    indexed --> superseded: newer_version_indexed
    failed --> uploaded: retry
    superseded --> [*]
```

**Extraction methods:**

| Method | Current | Future |
| --- | --- | --- |
| `native_text` | Supported | PDF, DOCX, HTML text extraction |
| `ocr` | Planned | Scanned PDFs and images |
| `connector_import` | Planned | External systems via IntegrationConnector |
| `manual_edit` | Planned | Human-authored corrections |

---

### Chunk

```mermaid
stateDiagram-v2
    [*] --> created
    created --> embedded: embedding_generated
    embedded --> indexed: vector_indexed
    indexed --> superseded: version_superseded
    superseded --> deleted: retention_cleanup
    deleted --> [*]
```

**Invariant:** Citations may reference `superseded` chunks for historical conversations.

---

### Embedding

```mermaid
stateDiagram-v2
    [*] --> pending
    pending --> computed: vector_created
    computed --> indexed: index_write_complete
    indexed --> stale: model_or_chunk_changed
    stale --> reindexed: recomputed
    reindexed --> indexed: index_write_complete
    indexed --> deleted: cleanup
    deleted --> [*]
```

## 4. AI configuration entities

### Embedding Model

```mermaid
stateDiagram-v2
    [*] --> available
    available --> enabled: org_enable
    enabled --> deprecated: platform_deprecate
    deprecated --> retired: migration_complete
    retired --> [*]
```

---

### LLM Provider

```mermaid
stateDiagram-v2
    [*] --> available
    available --> enabled: org_enable
    enabled --> degraded: provider_incident
    degraded --> enabled: recovered
    enabled --> disabled: admin_disable
    disabled --> retired: provider_removed
    retired --> [*]
```

---

### Prompt Template

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> approved: security_review
    approved --> active: publish
    active --> deprecated: newer_version
    deprecated --> retired: no_active_use
    retired --> [*]
```

**Invariant:** Only `approved` or `active` templates may be bound to production conversations.

---

### Retrieval Configuration

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> active: publish
    active --> deprecated: replacement_published
    deprecated --> retired: no_active_use
    retired --> [*]
```

## 5. Conversational entities

### Conversation

```mermaid
stateDiagram-v2
    [*] --> active
    active --> idle: inactivity_timeout
    idle --> active: new_message
    idle --> archived: user_or_policy_archive
    active --> archived: user_or_policy_archive
    archived --> deleted: retention_elapsed
    deleted --> [*]
```

---

### Message

```mermaid
stateDiagram-v2
    [*] --> submitted
    submitted --> retrieving: retrieval_started
    retrieving --> generating: context_assembled
    generating --> completed: answer_ready
    retrieving --> abstained: insufficient_evidence
    generating --> abstained: policy_block
    submitted --> failed: system_error
    retrieving --> failed: system_error
    generating --> failed: system_error
    completed --> [*]
    abstained --> [*]
    failed --> [*]
```

**Invariant:** `completed` and `abstained` messages are immutable except for moderation flags.

---

### Citation

```mermaid
stateDiagram-v2
    [*] --> proposed
    proposed --> attached: included_in_answer
    proposed --> rejected: failed_validation
    attached --> validated: reviewer_approval
    attached --> [*]
    rejected --> [*]
    validated --> [*]
```

## 6. Quality entities

### Evaluation

```mermaid
stateDiagram-v2
    [*] --> defined
    defined --> running: execution_started
    running --> passed: thresholds_met
    running --> failed: thresholds_missed
    passed --> archived: baseline_superseded
    failed --> archived: investigation_complete
    archived --> [*]
```

---

### Feedback

```mermaid
stateDiagram-v2
    [*] --> submitted
    submitted --> reviewed: triage_complete
    reviewed --> actioned: change_created
    reviewed --> dismissed: no_action
    actioned --> [*]
    dismissed --> [*]
```

## 7. Future integration entities

### IntegrationConnector

```mermaid
stateDiagram-v2
    [*] --> registered
    registered --> validated: connectivity_ok
    validated --> enabled: policy_approved
    enabled --> disabled: admin_disable
    disabled --> enabled: admin_enable
    disabled --> retired: connector_removed
    retired --> [*]
```

---

### ToolDefinition

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> approved: security_review
    approved --> enabled: publish
    enabled --> deprecated: replacement
    deprecated --> retired: no_active_use
    retired --> [*]
```

## 8. Cross-entity lifecycle rules

| Rule | Description |
| --- | --- |
| Version supersession | Publishing a new indexed `DocumentVersion` supersedes prior chunks for active retrieval but preserves citation lineage. |
| Model migration | Changing `EmbeddingModel` moves knowledge base to `reindexing` until required embeddings are `indexed`. |
| Configuration pinning | `Conversation` stores the retrieval, prompt, and provider versions used at creation time. |
| Safe deletion | `Organization` decommission cascades workspace archival; hard deletion follows retention policy. |
| Legal hold | Entities under hold cannot enter `deleted` regardless of user action. |

## 9. Related documents

- [Domain Model](DOMAIN_MODEL.md)
- [Ownership Model](OWNERSHIP_MODEL.md)
- [Permission Model](PERMISSION_MODEL.md)
