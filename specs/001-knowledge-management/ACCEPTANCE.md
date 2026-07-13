# Knowledge Management — Acceptance Criteria

> **Status:** Draft  
> **Format:** Given / When / Then (business-level, implementation-agnostic)

## 1. Knowledge base — happy path

### KB-AC-01 Create knowledge base

**Given** a user with `workspace:knowledge_base:create` in an active workspace  
**When** they create a knowledge base with a unique name and valid default language  
**Then** the system returns a knowledge base in `draft` status  
**And** the knowledge base is visible in the workspace knowledge base list  
**And** an audit record identifies the creator

### KB-AC-02 Publish knowledge base

**Given** a draft knowledge base and a user with `knowledge_base:manage`  
**When** they publish the knowledge base  
**Then** the knowledge base status becomes `active`  
**And** documents may be uploaded according to policy

### KB-AC-03 Archive and restore knowledge base

**Given** an active knowledge base with folders and documents  
**When** a knowledge admin archives the knowledge base  
**Then** the knowledge base, folders, and documents become `archived`  
**And** new uploads are rejected  
**When** the admin restores the knowledge base  
**Then** the knowledge base becomes `active`  
**And** child folders and documents remain archived until explicitly restored

---

## 2. Folder hierarchy — happy path

### KB-AC-04 Create nested folders

**Given** an active knowledge base and a user with `folder:manage`  
**When** they create a folder and a subfolder beneath it  
**Then** both folders appear in the tree under the correct parent  
**And** breadcrumb navigation reflects the hierarchy

### KB-AC-05 Move folder

**Given** a folder with documents in an active knowledge base  
**When** a user moves the folder to another active parent  
**Then** the folder and its subtree appear under the new parent  
**And** documents remain associated with their folder IDs  
**And** no cycle is created

---

## 3. Document upload — happy path

### KB-AC-06 Upload new document end-to-end

**Given** an active knowledge base and a user with `document:create`  
**When** they upload a supported PDF within size limits  
**Then** a document is created in `draft` status  
**And** version 1 is created with `processing_status` progressing toward `indexed`  
**And** the original file is retrievable by authorized download  
**And** an indexing event is emitted after commit

### KB-AC-07 Create new document version

**Given** an active document with an indexed version  
**When** a user with `document:update` uploads a replacement file and creates a new version  
**Then** version number increments by 1  
**And** the prior version remains in history  
**And** when indexing completes the new version may become current per policy

### KB-AC-08 Move document between folders

**Given** an active document in folder A  
**When** a user moves it to folder B  
**Then** the document appears only in folder B listings  
**And** version history is unchanged

---

## 4. Metadata

### KB-AC-09 Update document metadata

**Given** an active document  
**When** a user with `document:update` changes title, tags, and custom metadata  
**Then** subsequent reads reflect the updated metadata  
**And** document versions are not mutated

---

## 5. Lifecycle — archive, restore, delete

### KB-AC-10 Archive document

**Given** an active document  
**When** an authorized user archives it  
**Then** the document status is `archived`  
**And** it is excluded from default browse results  
**And** new versions cannot be uploaded

### KB-AC-11 Restore archived document

**Given** an archived document whose folder and knowledge base are active  
**When** an authorized user restores it  
**Then** the document status is `active`  
**And** it appears in browse results again

### KB-AC-12 Soft delete document

**Given** an active document without legal hold  
**When** a user with `document:delete` deletes it  
**Then** the document status is `deleted`  
**And** it is hidden from standard users  
**And** historical versions remain for audit

---

## 6. Bulk upload — happy path

### KB-AC-13 Bulk upload partial success

**Given** a batch of 5 valid files and a user with `document:create`  
**When** they complete bulk upload with 4 successful transfers and 1 failed transfer  
**Then** 4 documents and versions are created  
**And** the batch summary reports 4 succeeded and 1 failed  
**And** successful items are independently indexed

---

## 7. Invalid uploads

### KB-AC-14 File exceeds size limit

**Given** a maximum file size of 50 MB  
**When** a user initiates upload for a 60 MB file  
**Then** the request is rejected with a validation error  
**And** no upload session is created

### KB-AC-15 Upload session expired

**Given** an upload session older than the expiry window  
**When** the user attempts to complete the upload  
**Then** the completion is rejected with a conflict error  
**And** staged content is not promoted to a document version

### KB-AC-16 Content hash mismatch

**Given** a completed upload with declared SHA-256 hash  
**When** the stored object hash does not match  
**Then** completion fails with validation error  
**And** no document version is created

### KB-AC-17 Empty file

**Given** a zero-byte file  
**When** a user attempts to upload it  
**Then** the upload is rejected  
**And** no version is created

---

## 8. Duplicate names

### KB-AC-18 Duplicate knowledge base name

**Given** an active knowledge base named "Policies" in a workspace  
**When** a user creates another knowledge base named "Policies"  
**Then** the request is rejected with a conflict error

### KB-AC-19 Duplicate folder name among siblings

**Given** a folder named "HR" under the knowledge base root  
**When** a user creates another folder named "HR" under the same parent  
**Then** the request is rejected with a conflict error

### KB-AC-20 Duplicate document title (policy off)

**Given** title uniqueness is not enforced  
**When** two documents share the same title in one folder  
**Then** both documents are created successfully  
**And** they remain distinct by ID

---

## 9. Archived objects

### KB-AC-21 Upload to archived knowledge base

**Given** an archived knowledge base  
**When** a user attempts to initiate an upload  
**Then** the request is forbidden or conflict per policy  
**And** no upload session is created

### KB-AC-22 Modify archived document

**Given** an archived document  
**When** a user attempts to update metadata  
**Then** the request is rejected with a conflict error

### KB-AC-23 Restore document under archived folder

**Given** a document archived as part of folder archive  
**When** a user restores the document before restoring the parent folder  
**Then** the restore fails with guidance to restore the parent folder first

---

## 10. Deleted objects

### KB-AC-24 Access deleted document by ID

**Given** a soft-deleted document  
**When** a standard user requests the document by ID  
**Then** the response is not found or forbidden  
**And** no metadata or download URL is exposed

### KB-AC-25 Admin list with deleted filter

**Given** a user with elevated knowledge admin permission  
**When** they list documents with `include_deleted=true`  
**Then** deleted documents appear with `deleted` status  
**And** download remains policy-controlled

### KB-AC-26 Delete with legal hold

**Given** a document with `legal_hold = true`  
**When** a user attempts to delete it  
**Then** the delete is rejected with a conflict error  
**And** the document status is unchanged

---

## 11. Version conflicts

### KB-AC-27 Concurrent version creation

**Given** two concurrent requests to create a new version for the same document  
**When** both use distinct completed uploads  
**Then** exactly one receives version N and the other version N+1  
**And** no duplicate `version_number` exists

### KB-AC-28 Reuse completed upload

**Given** an upload already bound to version 2  
**When** a client attempts to create another version with the same upload ID  
**Then** the request is rejected with a conflict error

### KB-AC-29 Optimistic concurrency on document

**Given** a document at entity version 3  
**When** a user submits an update with `expected_version` 2  
**Then** the update is rejected with a conflict error  
**And** no metadata change is applied

---

## 12. Large files

### KB-AC-30 Large file within limit

**Given** a 49 MB supported file  
**When** a user uploads it through the standard flow  
**Then** upload completes successfully  
**And** a version row records the correct `file_size_bytes`

### KB-AC-31 Multipart large upload (if enabled)

**Given** multipart upload is enabled for files over 10 MB  
**When** a user uploads a 40 MB file in parts  
**Then** all parts assemble into one object  
**And** complete upload succeeds with matching size

---

## 13. Unsupported formats

### KB-AC-32 Reject executable upload

**Given** a user uploads a `.exe` file disguised with a PDF extension  
**When** the server inspects content type and magic bytes  
**Then** the upload is rejected after detection  
**And** no version enters the indexing pipeline

### KB-AC-33 Reject unsupported image in v1

**Given** OCR is not enabled  
**When** a user uploads a PNG image  
**Then** the upload is rejected as unsupported format  
**And** the error identifies allowed formats

---

## 14. Authorization

### KB-AC-34 Viewer cannot upload

**Given** a user with only `document:read`  
**When** they attempt to initiate an upload  
**Then** the request is forbidden

### KB-AC-35 Restricted document access

**Given** a document with `classification_label = restricted` and no ACL for user B  
**When** user B requests the document  
**Then** the response is not found or forbidden  
**And** list endpoints exclude the document

### KB-AC-36 Download requires permission

**Given** a user with `document:read` but not `document:download`  
**When** they request version download  
**Then** the request is forbidden

---

## 15. Idempotency

### KB-AC-37 Idempotent knowledge base create

**Given** a create request with `X-Idempotency-Key`  
**When** the client retries the same request after a timeout  
**Then** only one knowledge base exists  
**And** the retry returns the original resource

### KB-AC-38 Idempotent archive

**Given** an archived document  
**When** the archive command is submitted again  
**Then** the operation succeeds without error  
**And** status remains `archived`

---

## 16. Future multilingual support

### KB-AC-39 Declare document language

**Given** a knowledge base with default language `en`  
**When** a user creates a document with `declared_language = fr`  
**Then** the document stores `fr` as declared language  
**And** indexing may use language-aware chunking when available

### KB-AC-40 KB default language inheritance

**Given** a knowledge base with `default_language = de`  
**When** a user creates a document without specifying language  
**Then** the document `declared_language` is `de`

### KB-AC-41 Future multilingual segments (planned)

**Given** a future document version with multilingual segment maps  
**When** content contains multiple languages  
**Then** each segment stores its own BCP-47 language code  
**And** retrieval can filter by segment language without changing the document identity

### KB-AC-42 Future OCR for scanned content (planned)

**Given** OCR connector is enabled for the workspace  
**When** a user uploads a scanned PDF  
**Then** a version is created with `extraction_method = ocr`  
**And** text extraction runs asynchronously before chunking

---

## 17. Observability and audit

### KB-AC-43 Audit on delete

**Given** a successful document delete  
**When** an auditor reviews tenant audit logs  
**Then** an entry records actor, document ID, timestamp, and correlation ID

### KB-AC-44 Correlation across upload pipeline

**Given** an API request with `X-Correlation-ID`  
**When** upload triggers async indexing  
**Then** downstream logs include the same correlation ID

---

## Traceability matrix

| Acceptance ID | Primary API | Primary workflow |
| --- | --- | --- |
| KB-AC-01–03 | Knowledge base endpoints | Create / archive KB |
| KB-AC-04–05 | Folder endpoints | Folder hierarchy |
| KB-AC-06–08 | Upload + document + version | Upload document |
| KB-AC-09 | Metadata | Update metadata |
| KB-AC-10–12 | Status endpoints | Archive / restore / delete |
| KB-AC-13 | Bulk upload | Bulk upload |
| KB-AC-14–17 | Upload validation | Upload document |
| KB-AC-18–20 | Create endpoints | Name validation |
| KB-AC-21–23 | Status gates | Archived objects |
| KB-AC-24–26 | Delete / list | Deleted objects |
| KB-AC-27–29 | Version + PATCH | Version conflicts |
| KB-AC-30–31 | Upload | Large files |
| KB-AC-32–33 | Upload | Unsupported formats |
| KB-AC-34–36 | All read/write | Authorization |
| KB-AC-37–38 | Mutations | Idempotency |
| KB-AC-39–42 | Metadata / future | Multilingual / OCR |
| KB-AC-43–44 | Cross-cutting | Audit / observability |

---

## Related documents

- [README.md](README.md)
- [API.md](API.md)
- [VALIDATION.md](VALIDATION.md)
- [WORKFLOWS.md](WORKFLOWS.md)
