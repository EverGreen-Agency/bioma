from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.files import ClientFileDownloadResponse, ClientFileSummary, ClientFileVisibility
from bioma_api.services import files as files_service


router = APIRouter(prefix="/clients/{client_id}/files", tags=["files"])
workspace_router = APIRouter(prefix="/workspaces/{client_id}/files", tags=["workspace-files"])


@router.get("", response_model=list[ClientFileSummary])
@workspace_router.get("", response_model=list[ClientFileSummary])
def list_files(
    client_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[ClientFileSummary]:
    return files_service.list_files(client_id, user)


@router.post("", response_model=list[ClientFileSummary], status_code=status.HTTP_201_CREATED)
@workspace_router.post("", response_model=list[ClientFileSummary], status_code=status.HTTP_201_CREATED)
def upload_file(
    client_id: UUID,
    file: UploadFile = File(...),
    visibility: ClientFileVisibility = Form("client"),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[ClientFileSummary]:
    return files_service.upload_file(client_id, file, visibility, user)


@router.get("/{file_id}/download", response_model=ClientFileDownloadResponse)
@workspace_router.get("/{file_id}/download", response_model=ClientFileDownloadResponse)
def download_file(
    client_id: UUID,
    file_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ClientFileDownloadResponse:
    return files_service.request_download(client_id, file_id, user)


@router.delete("/{file_id}", response_model=list[ClientFileSummary])
@workspace_router.delete("/{file_id}", response_model=list[ClientFileSummary])
def delete_file(
    client_id: UUID,
    file_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[ClientFileSummary]:
    return files_service.delete_file(client_id, file_id, user)
