"""Knowledge management API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, Request, Response, status

from rag_enterprise.api.common.pagination import PaginatedEnvelope, paginated_response
from rag_enterprise.api.common.responses import SuccessEnvelope, success_response
from rag_enterprise.knowledge import commands as cmd
from rag_enterprise.knowledge import queries as qry
from rag_enterprise.knowledge.api.dependencies import (
    ActorDep,
    CommandDispatcherDep,
    QueryDispatcherDep,
    raise_for_result,
)
from rag_enterprise.knowledge.dto import (
    CreateDocumentRequest,
    CreateDocumentVersionRequest,
    CreateFolderRequest,
    CreateKnowledgeBaseRequest,
    DocumentDetailDTO,
    DocumentVersionSummaryDTO,
    FolderContentsDTO,
    FolderSummaryDTO,
    InitiateUploadRequest,
    KnowledgeBaseDetailDTO,
    KnowledgeBaseSummaryDTO,
    MoveDocumentRequest,
    MoveFolderRequest,
    TreeViewDTO,
    UpdateDocumentMetadataRequest,
    UpdateKnowledgeBaseRequest,
    UploadSessionDTO,
)
from rag_enterprise.knowledge.mappers import (
    to_document_detail,
    to_folder_summary,
    to_version_summary,
)

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["knowledge-bases"])


@router.get("/knowledge-bases", response_model=PaginatedEnvelope[KnowledgeBaseSummaryDTO])
async def list_knowledge_bases(
    workspace_id: uuid.UUID,
    actor: ActorDep,
    dispatcher: QueryDispatcherDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = None,
) -> PaginatedEnvelope[KnowledgeBaseSummaryDTO]:
    result = await dispatcher.dispatch(
        qry.ListKnowledgeBasesQuery(
            actor=actor,
            workspace_id=workspace_id,
            status=status_filter,
            query=q,
            page=page,
            page_size=page_size,
        )
    )
    return paginated_response(raise_for_result(result))


@router.post(
    "/knowledge-bases",
    response_model=SuccessEnvelope[KnowledgeBaseDetailDTO],
    status_code=status.HTTP_201_CREATED,
)
async def create_knowledge_base(
    workspace_id: uuid.UUID,
    body: CreateKnowledgeBaseRequest,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> SuccessEnvelope[KnowledgeBaseDetailDTO]:
    result = await dispatcher.dispatch(
        cmd.CreateKnowledgeBaseCommand(
            actor=actor,
            workspace_id=workspace_id,
            name=body.name,
            default_language=body.default_language,
            visibility_policy=body.visibility_policy,
            description=body.description,
        )
    )
    return success_response(raise_for_result(result))


@router.get(
    "/knowledge-bases/{knowledge_base_id}",
    response_model=SuccessEnvelope[KnowledgeBaseDetailDTO],
)
async def get_knowledge_base(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    actor: ActorDep,
    dispatcher: QueryDispatcherDep,
) -> SuccessEnvelope[KnowledgeBaseDetailDTO]:
    result = await dispatcher.dispatch(
        qry.GetKnowledgeBaseQuery(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
        )
    )
    return success_response(raise_for_result(result))


@router.patch(
    "/knowledge-bases/{knowledge_base_id}",
    response_model=SuccessEnvelope[KnowledgeBaseDetailDTO],
)
async def update_knowledge_base(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    body: UpdateKnowledgeBaseRequest,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> SuccessEnvelope[KnowledgeBaseDetailDTO]:
    result = await dispatcher.dispatch(
        cmd.UpdateKnowledgeBaseCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            name=body.name,
            default_language=body.default_language,
            visibility_policy=body.visibility_policy,
            description=body.description,
            expected_version=body.expected_version,
        )
    )
    return success_response(raise_for_result(result))


@router.post(
    "/knowledge-bases/{knowledge_base_id}/publish",
    response_model=SuccessEnvelope[KnowledgeBaseDetailDTO],
)
async def publish_knowledge_base(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> SuccessEnvelope[KnowledgeBaseDetailDTO]:
    result = await dispatcher.dispatch(
        cmd.PublishKnowledgeBaseCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
        )
    )
    return success_response(raise_for_result(result))


@router.post(
    "/knowledge-bases/{knowledge_base_id}/archive",
    response_model=SuccessEnvelope[KnowledgeBaseDetailDTO],
)
async def archive_knowledge_base(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> SuccessEnvelope[KnowledgeBaseDetailDTO]:
    result = await dispatcher.dispatch(
        cmd.ArchiveKnowledgeBaseCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
        )
    )
    return success_response(raise_for_result(result))


@router.post(
    "/knowledge-bases/{knowledge_base_id}/restore",
    response_model=SuccessEnvelope[KnowledgeBaseDetailDTO],
)
async def restore_knowledge_base(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> SuccessEnvelope[KnowledgeBaseDetailDTO]:
    result = await dispatcher.dispatch(
        cmd.RestoreKnowledgeBaseCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
        )
    )
    return success_response(raise_for_result(result))


@router.delete("/knowledge-bases/{knowledge_base_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> Response:
    result = await dispatcher.dispatch(
        cmd.DeleteKnowledgeBaseCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
        )
    )
    raise_for_result(result)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/knowledge-bases/{knowledge_base_id}/folders",
    response_model=SuccessEnvelope[FolderSummaryDTO],
    status_code=status.HTTP_201_CREATED,
    tags=["folders"],
)
async def create_folder(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    body: CreateFolderRequest,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> SuccessEnvelope[FolderSummaryDTO]:
    result = await dispatcher.dispatch(
        cmd.CreateFolderCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            name=body.name,
            parent_folder_id=body.parent_folder_id,
        )
    )
    return success_response(to_folder_summary(raise_for_result(result)))


@router.post(
    "/knowledge-bases/{knowledge_base_id}/folders/{folder_id}/move",
    response_model=SuccessEnvelope[FolderSummaryDTO],
    tags=["folders"],
)
async def move_folder(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    folder_id: uuid.UUID,
    body: MoveFolderRequest,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> SuccessEnvelope[FolderSummaryDTO]:
    result = await dispatcher.dispatch(
        cmd.MoveFolderCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            folder_id=folder_id,
            target_parent_folder_id=body.target_parent_folder_id,
            expected_version=body.expected_version,
        )
    )
    return success_response(to_folder_summary(raise_for_result(result)))


@router.delete(
    "/knowledge-bases/{knowledge_base_id}/folders/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["folders"],
)
async def delete_folder(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    folder_id: uuid.UUID,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> Response:
    result = await dispatcher.dispatch(
        cmd.DeleteFolderCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            folder_id=folder_id,
        )
    )
    raise_for_result(result)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/knowledge-bases/{knowledge_base_id}/tree",
    response_model=SuccessEnvelope[TreeViewDTO],
    tags=["folders"],
)
async def get_tree(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    actor: ActorDep,
    dispatcher: QueryDispatcherDep,
    depth: int = Query(default=3, ge=1, le=10),
) -> SuccessEnvelope[TreeViewDTO]:
    result = await dispatcher.dispatch(
        qry.TreeViewQuery(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            depth=depth,
        )
    )
    return success_response(raise_for_result(result))


@router.get(
    "/knowledge-bases/{knowledge_base_id}/contents",
    response_model=SuccessEnvelope[FolderContentsDTO],
    tags=["folders"],
)
async def folder_contents(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    actor: ActorDep,
    dispatcher: QueryDispatcherDep,
    folder_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> SuccessEnvelope[FolderContentsDTO]:
    result = await dispatcher.dispatch(
        qry.FolderContentsQuery(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            folder_id=folder_id,
            page=page,
            page_size=page_size,
        )
    )
    return success_response(raise_for_result(result))


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=SuccessEnvelope[DocumentDetailDTO],
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
async def create_document(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    body: CreateDocumentRequest,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> SuccessEnvelope[DocumentDetailDTO]:
    result = await dispatcher.dispatch(
        cmd.CreateDocumentCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            title=body.title,
            folder_id=body.folder_id,
            declared_language=body.declared_language,
            source_type=body.source_type,
            classification_label=body.classification_label,
            tags=body.tags,
            metadata=body.metadata,
        )
    )
    return success_response(to_document_detail(raise_for_result(result)))


@router.get(
    "/knowledge-bases/{knowledge_base_id}/documents/{document_id}",
    response_model=SuccessEnvelope[DocumentDetailDTO],
    tags=["documents"],
)
async def get_document(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    document_id: uuid.UUID,
    actor: ActorDep,
    dispatcher: QueryDispatcherDep,
) -> SuccessEnvelope[DocumentDetailDTO]:
    result = await dispatcher.dispatch(
        qry.DocumentDetailsQuery(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
        )
    )
    return success_response(raise_for_result(result))


@router.patch(
    "/knowledge-bases/{knowledge_base_id}/documents/{document_id}",
    response_model=SuccessEnvelope[DocumentDetailDTO],
    tags=["documents"],
)
async def update_document_metadata(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    document_id: uuid.UUID,
    body: UpdateDocumentMetadataRequest,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> SuccessEnvelope[DocumentDetailDTO]:
    result = await dispatcher.dispatch(
        cmd.UpdateDocumentMetadataCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            title=body.title,
            declared_language=body.declared_language,
            classification_label=body.classification_label,
            tags=body.tags,
            metadata=body.metadata,
            expected_version=body.expected_version,
        )
    )
    return success_response(to_document_detail(raise_for_result(result)))


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents/{document_id}/move",
    response_model=SuccessEnvelope[DocumentDetailDTO],
    tags=["documents"],
)
async def move_document(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    document_id: uuid.UUID,
    body: MoveDocumentRequest,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> SuccessEnvelope[DocumentDetailDTO]:
    result = await dispatcher.dispatch(
        cmd.MoveDocumentCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            target_folder_id=body.target_folder_id,
        )
    )
    return success_response(to_document_detail(raise_for_result(result)))


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents/{document_id}/archive",
    response_model=SuccessEnvelope[DocumentDetailDTO],
    tags=["documents"],
)
async def archive_document(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    document_id: uuid.UUID,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> SuccessEnvelope[DocumentDetailDTO]:
    result = await dispatcher.dispatch(
        cmd.ArchiveDocumentCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
        )
    )
    return success_response(to_document_detail(raise_for_result(result)))


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents/{document_id}/restore",
    response_model=SuccessEnvelope[DocumentDetailDTO],
    tags=["documents"],
)
async def restore_document(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    document_id: uuid.UUID,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> SuccessEnvelope[DocumentDetailDTO]:
    result = await dispatcher.dispatch(
        cmd.RestoreDocumentCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
        )
    )
    return success_response(to_document_detail(raise_for_result(result)))


@router.delete(
    "/knowledge-bases/{knowledge_base_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["documents"],
)
async def delete_document(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    document_id: uuid.UUID,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> Response:
    result = await dispatcher.dispatch(
        cmd.DeleteDocumentCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
        )
    )
    raise_for_result(result)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/knowledge-bases/{knowledge_base_id}/uploads",
    response_model=SuccessEnvelope[UploadSessionDTO],
    status_code=status.HTTP_201_CREATED,
    tags=["uploads"],
)
async def initiate_upload(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    body: InitiateUploadRequest,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> SuccessEnvelope[UploadSessionDTO]:
    result = await dispatcher.dispatch(
        cmd.InitiateUploadCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            file_name=body.file_name,
            file_size_bytes=body.file_size_bytes,
            mime_type=body.mime_type,
            document_id=body.document_id,
            checksum_sha256=body.checksum_sha256,
        )
    )
    return success_response(raise_for_result(result))


@router.post(
    "/knowledge-bases/{knowledge_base_id}/uploads/{upload_id}/complete",
    response_model=SuccessEnvelope[UploadSessionDTO],
    tags=["uploads"],
)
async def complete_upload(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    upload_id: uuid.UUID,
    request: Request,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> SuccessEnvelope[UploadSessionDTO]:
    content = await request.body()
    result = await dispatcher.dispatch(
        cmd.CompleteUploadCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            upload_id=upload_id,
            content=content,
        )
    )
    return success_response(raise_for_result(result))


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents/{document_id}/versions",
    response_model=SuccessEnvelope[DocumentVersionSummaryDTO],
    status_code=status.HTTP_201_CREATED,
    tags=["document-versions"],
)
async def create_document_version(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    document_id: uuid.UUID,
    body: CreateDocumentVersionRequest,
    actor: ActorDep,
    dispatcher: CommandDispatcherDep,
) -> SuccessEnvelope[DocumentVersionSummaryDTO]:
    result = await dispatcher.dispatch(
        cmd.UploadDocumentVersionCommand(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            upload_id=body.upload_id,
            change_summary=body.change_summary,
        )
    )
    version = raise_for_result(result)
    return success_response(
        to_version_summary(version, current_version_id=version.id),
    )


@router.get(
    "/knowledge-bases/{knowledge_base_id}/search",
    response_model=PaginatedEnvelope[DocumentDetailDTO],
    tags=["documents"],
)
async def search_metadata(
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    actor: ActorDep,
    dispatcher: QueryDispatcherDep,
    q: str = Query(min_length=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedEnvelope[DocumentDetailDTO]:
    result = await dispatcher.dispatch(
        qry.SearchMetadataQuery(
            actor=actor,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            query=q,
            page=page,
            page_size=page_size,
        )
    )
    return paginated_response(raise_for_result(result))
