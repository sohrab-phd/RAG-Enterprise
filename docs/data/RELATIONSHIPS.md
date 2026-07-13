# Relationships

> **Status:** Accepted — implementation-ready relationship design.  
> **Purpose:** Document cardinality, ownership, cascade behavior, delete policy, and orphan policy for all major relationships.

## 1. Relationship conventions

| Term | Meaning |
| --- | --- |
| Ownership | Parent aggregate controls child lifecycle |
| Cascade | Automatic child mutation or deletion triggered by parent action |
| Delete policy | What happens on parent delete |
| Orphan policy | What happens if child loses parent reference |
| Restrict | Parent delete blocked while children exist |

Default delete policy for tenant-owned data: **soft archive first, hard delete by retention job**.
Default FK behavior in implementation: **RESTRICT**, unless explicitly listed below.

## 2. One-to-one relationships

| Parent | Child | Ownership | Cascade | Delete policy | Orphan policy |
| --- | --- | --- | --- | --- | --- |
| `Document` | current `DocumentVersion` pointer | Document | update pointer on new version | pointer nulled only when document deleted | not allowed; latest indexed version must be resolvable |
| `Conversation` | latest `Message` pointer optional | Conversation | update on append | delete with conversation | not allowed |
| `IntegrationConnector` | connector health snapshot optional | Connector | update on validation | delete with connector retirement | snapshot removed with connector |

**Implementation note:** Current-version pointers are mutable references to immutable version rows.

## 3. One-to-many relationships

### Tenant administration

| Parent | Child | Ownership | Cascade | Delete policy | Orphan policy |
| --- | --- | --- | --- | --- | --- |
| `Organization` | `Workspace` | Organization | none | restrict while workspaces active; decommission archives all | not allowed |
| `Organization` | `Role` | Organization | none | restrict while memberships reference role | not allowed |
| `Organization` | `Membership` | Organization | soft revoke | decommission revokes all | not allowed |
| `Workspace` | `KnowledgeBase` | Workspace | archive | workspace archive cascades KB archive | not allowed |
| `Workspace` | `Conversation` | Workspace | archive | workspace archive blocks new conversations | not allowed |
| `Workspace` | `IntegrationConnector` | Workspace | disable | connector disabled on workspace archive | not allowed |
| `User` | `Membership` | Organization via membership | none | user delete revokes memberships | not allowed |
| `Role` | `Membership` | Organization | none | role deprecation retains memberships | not allowed |

### Knowledge content

| Parent | Child | Ownership | Cascade | Delete policy | Orphan policy |
| --- | --- | --- | --- | --- | --- |
| `KnowledgeBase` | `Folder` | KnowledgeBase | archive subtree | KB delete archives folders | not allowed |
| `KnowledgeBase` | `Document` | KnowledgeBase | archive | KB delete archives documents | not allowed |
| `KnowledgeBase` | `RetrievalConfiguration` | KnowledgeBase | deprecate active | KB delete retires configurations | not allowed |
| `Folder` | child `Folder` | KnowledgeBase | move/archive subtree | folder delete requires empty or cascade policy | not allowed |
| `Folder` | `Document` | KnowledgeBase | move with folder | folder delete moves docs to root or blocks | not allowed |
| `Document` | `DocumentVersion` | Document | none | document delete retains versions for citation/legal hold | not allowed |
| `DocumentVersion` | `Chunk` | Indexing | supersede | version supersession marks chunks superseded | chunks never orphaned; always retain version FK |

### Indexing

| Parent | Child | Ownership | Cascade | Delete policy | Orphan policy |
| --- | --- | --- | --- | --- | --- |
| `Chunk` | `Embedding` | Indexing | mark stale | chunk delete marks embeddings deleted after retention | not allowed |
| `EmbeddingModel` | `Embedding` | Indexing | none | model retirement marks embeddings stale | not allowed |

### Conversational experience

| Parent | Child | Ownership | Cascade | Delete policy | Orphan policy |
| --- | --- | --- | --- | --- | --- |
| `Conversation` | `Message` | Conversation | delete with retention | conversation delete removes messages per policy | not allowed |
| `Message` | `Citation` | Conversation | delete with message | message retained implies citations retained | not allowed |

### AI configuration

| Parent | Child | Ownership | Cascade | Delete policy | Orphan policy |
| --- | --- | --- | --- | --- | --- |
| `Organization` | `PromptTemplate` | Organization | retire | org decommission retires templates | not allowed |
| `LLMProvider` | `PromptTemplate` | PromptTemplate aggregate | none | provider retirement blocks new prompts | existing versions remain historical |
| `KnowledgeBase` | `Evaluation` | Evaluation | archive | KB delete archives evaluations | not allowed |
| `RetrievalConfiguration` | `Evaluation` | Evaluation | none | config retirement retains historical evaluation links | not allowed |

### Quality and integrations

| Parent | Child | Ownership | Cascade | Delete policy | Orphan policy |
| --- | --- | --- | --- | --- | --- |
| `Message` | `Feedback` | Evaluation/quality | none | message delete anonymizes or deletes feedback per policy | not allowed |
| `Citation` | `Feedback` optional | Quality | none | citation retained while feedback exists | feedback may exist without citation |
| `IntegrationConnector` | `ToolDefinition` | Connector | retire | connector retirement disables tools | not allowed |

## 4. Many-to-many relationships

Many-to-many relationships are implemented through explicit join entities.

| Left entity | Right entity | Join entity | Ownership | Delete policy | Orphan policy |
| --- | --- | --- | --- | --- | --- |
| `Organization` | `EmbeddingModel` | `organization_embedding_model` | Organization | remove enablement on decommission | join row deleted |
| `Organization` | `LLMProvider` | `organization_llm_provider` | Organization | remove enablement on decommission | join row deleted |
| `User` | `Workspace` | `Membership` | Organization | revoke on workspace or user removal | not allowed |
| `User` | `Role` | `Membership` | Organization | role change updates join | not allowed |
| `KnowledgeBase` | `EmbeddingModel` | via `RetrievalConfiguration` | KnowledgeBase | implicit through active config | historical configs retain reference |
| `Conversation` | `ToolDefinition` future | `conversation_tool_invocation` | Conversation | conversation delete archives invocations | invocation logs never orphaned |
| `Document` | `User` editors/viewers | `document_acl` | Document | document delete removes ACL rows | ACL row deleted with document |
| `KnowledgeBase` | `Workspace` shared visibility future | `knowledge_base_share` | Organization | share revoked on KB archive | join row deleted |

## 5. Reference-only relationships

These are foreign keys without ownership cascade.

| From | To | Purpose | Delete policy |
| --- | --- | --- | --- |
| `Citation` | `Chunk` | Evidence lineage | restrict if chunk purge would break retained citation |
| `Conversation` | `RetrievalConfiguration` | Pinned policy version | retain historical FK |
| `Conversation` | `PromptTemplate` | Pinned prompt version | retain historical FK |
| `Conversation` | `LLMProvider` | Pinned provider | retain historical FK |
| `Message` | `Chunk` via `Citation` | Answer evidence | historical only |
| `Evaluation` | `KnowledgeBase` | Benchmark scope | retain |
| `Evaluation` | `RetrievalConfiguration` | Benchmark config | retain |

## 6. Cascade matrix by operation

| Operation | Cascading behavior |
| --- | --- |
| Organization decommission | Revoke memberships; archive workspaces; disable connectors; retain audit/evaluation history |
| Workspace archive | Archive knowledge bases and conversations; block new ingestion |
| Knowledge base archive | Archive documents and folders; block new retrieval except admin audit |
| Document delete | Soft delete document; retain versions, chunks, citations per policy |
| Document version supersede | Mark chunks superseded; embeddings become stale |
| Embedding model migration | Create new embeddings; stale old ones; no delete until re-index complete |
| Conversation delete | Soft delete conversation and messages; retain citations if legal hold |
| Connector retire | Disable tools; retain connector and tool history |

## 7. Orphan prevention rules

| Rule | Enforcement |
| --- | --- |
| No tenantless business rows | Application validates parent scope on insert |
| No chunk without version | DB FK + ingestion workflow guard |
| No embedding without chunk | DB FK |
| No citation without message | DB FK |
| No active retrieval config without KB | DB FK + publication guard |
| No enabled tool without connector | DB FK + approval guard |
| Historical references survive supersession | Status-based filtering, not FK nulling |

## 8. Future relationship extensions

| Future capability | Relationship addition |
| --- | --- |
| OCR | `DocumentVersion` child table `document_extraction_artifact` |
| Web search | `Citation` optional `external_evidence_id` referencing ephemeral evidence store |
| SQL agent | `ToolDefinition` → `sql_data_source` one-to-one config child |
| MCP | `IntegrationConnector` one-to-many `ToolDefinition` with `source = mcp` |
| Multilingual segments | `DocumentVersion` one-to-many `content_segment` with `language` |

## 9. Related documents

- [Data Architecture](DATA_ARCHITECTURE.md)
- [Aggregates](AGGREGATES.md)
- [Data Lifecycle](DATA_LIFECYCLE.md)
