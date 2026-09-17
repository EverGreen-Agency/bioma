"""HTTP do Wiki EG (base de conhecimento interna). Só platform_admin."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.wiki import (
    WikiAttachmentDownload,
    WikiAttachmentSummary,
    WikiDocumentCreate,
    WikiDocumentDetail,
    WikiDocumentSummary,
    WikiDocumentUpdate,
    WikiImportResult,
)
from bioma_api.services import wiki as wiki_service

router = APIRouter(prefix="/backoffice/wiki", tags=["wiki"])


@router.get("/documents", response_model=list[WikiDocumentSummary])
def list_documents(user: CurrentUserResponse = Depends(current_user_from_request)):
    return wiki_service.list_documents(user)


@router.post("/import-core", response_model=WikiImportResult)
def import_core_documents(user: CurrentUserResponse = Depends(current_user_from_request)):
    return wiki_service.import_core_documents(user)


@router.post("/documents", response_model=WikiDocumentDetail, status_code=status.HTTP_201_CREATED)
def create_document(payload: WikiDocumentCreate, user: CurrentUserResponse = Depends(current_user_from_request)):
    return wiki_service.create_document(payload, user)


@router.get("/documents/{document_id}", response_model=WikiDocumentDetail)
def get_document(document_id: UUID, user: CurrentUserResponse = Depends(current_user_from_request)):
    return wiki_service.get_document(document_id, user)


@router.patch("/documents/{document_id}", response_model=WikiDocumentDetail)
def update_document(
    document_id: UUID, payload: WikiDocumentUpdate, user: CurrentUserResponse = Depends(current_user_from_request)
):
    return wiki_service.update_document(document_id, payload, user)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: UUID, user: CurrentUserResponse = Depends(current_user_from_request)):
    wiki_service.delete_document(document_id, user)


@router.post(
    "/documents/{document_id}/attachments",
    response_model=WikiAttachmentSummary,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    document_id: UUID,
    file: UploadFile = File(...),
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return await wiki_service.add_attachment(document_id, file, user)


@router.get("/attachments/{attachment_id}/download", response_model=WikiAttachmentDownload)
def download_attachment(attachment_id: UUID, user: CurrentUserResponse = Depends(current_user_from_request)):
    return wiki_service.download_attachment(attachment_id, user)


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(attachment_id: UUID, user: CurrentUserResponse = Depends(current_user_from_request)):
    wiki_service.delete_attachment(attachment_id, user)
