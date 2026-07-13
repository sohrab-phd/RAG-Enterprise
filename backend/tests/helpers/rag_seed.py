"""Shared seeding helpers for indexing and retrieval tests."""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from rag_enterprise.db.types import generate_uuid7
from rag_enterprise.indexing.enums import ChunkStatus
from rag_enterprise.indexing.models import Chunk
from rag_enterprise.knowledge.authorization import ALL_KNOWLEDGE_PERMISSIONS
from rag_enterprise.knowledge.enums import (
    DocumentStatus,
    KnowledgeBaseStatus,
    ProcessingStatus,
)
from rag_enterprise.knowledge.models import Document, DocumentVersion, KnowledgeBase

ALL_PERMISSIONS = frozenset(ALL_KNOWLEDGE_PERMISSIONS)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def seed_chunked_version(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    texts: list[str],
    languages: list[str] | None = None,
    kb_status: str = KnowledgeBaseStatus.ACTIVE,
    document_status: str = DocumentStatus.ACTIVE,
    version_status: str = ProcessingStatus.CHUNKED,
) -> tuple[KnowledgeBase, Document, DocumentVersion, list[Chunk]]:
    kb = KnowledgeBase(
        organization_id=org_id,
        workspace_id=workspace_id,
        name=f"KB-{generate_uuid7()}",
        status=kb_status,
        default_language="fa",
    )
    session.add(kb)
    await session.flush()

    document = Document(
        organization_id=org_id,
        workspace_id=workspace_id,
        knowledge_base_id=kb.id,
        title="Sample",
        status=document_status,
        declared_language="fa",
    )
    session.add(document)
    await session.flush()

    version = DocumentVersion(
        organization_id=org_id,
        workspace_id=workspace_id,
        knowledge_base_id=kb.id,
        document_id=document.id,
        version_number=1,
        processing_status=version_status,
        content_hash=content_hash("original"),
        file_name="sample.txt",
        file_size_bytes=100,
        mime_type="text/plain",
        storage_key_original="original/key",
        storage_key_extracted="extracted/key",
    )
    session.add(version)
    await session.flush()
    document.current_version_id = version.id

    chunks: list[Chunk] = []
    offset = 0
    for index, text in enumerate(texts):
        language = None if languages is None else languages[index]
        chunk = Chunk(
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb.id,
            document_id=document.id,
            document_version_id=version.id,
            sequence_number=index,
            text=text,
            content_hash=content_hash(text),
            start_offset=offset,
            end_offset=offset + len(text),
            language=language,
            strategy="paragraph",
            status=ChunkStatus.CREATED,
        )
        offset += len(text) + 2
        session.add(chunk)
        chunks.append(chunk)

    await session.commit()
    for chunk in chunks:
        await session.refresh(chunk)
    await session.refresh(version)
    await session.refresh(document)
    await session.refresh(kb)
    return kb, document, version, chunks
