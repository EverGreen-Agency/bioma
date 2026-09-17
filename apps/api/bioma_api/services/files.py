import re
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status

from bioma_api.access import is_platform_admin, resolve_accessible_client
from bioma_api.config import get_settings
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import files as files_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.files import ClientFileDownloadResponse, ClientFileSummary, ClientFileVisibility
from bioma_api.services import storage
from bioma_api.services.storage import StorageNotConfiguredError, StorageOperationError


def list_files(client_id: UUID, user: CurrentUserResponse) -> list[ClientFileSummary]:
    with connect() as conn:
        client = _accessible_client(conn, client_id, user)
        rows = files_repo.list_files(conn, client["organization_id"], is_platform_admin(user))
    return [ClientFileSummary(**row) for row in rows]


def upload_file(
    client_id: UUID,
    upload: UploadFile,
    visibility: ClientFileVisibility,
    user: CurrentUserResponse,
) -> list[ClientFileSummary]:
    settings = get_settings()

    file_name = (upload.filename or "arquivo").strip()
    if not file_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nome do arquivo é obrigatório.")

    content = upload.file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Arquivo vazio.")

    max_bytes = settings.storage_max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo maior que o limite de {settings.storage_max_upload_mb} MB.",
        )

    content_type = upload.content_type or "application/octet-stream"

    with connect() as conn:
        client = _accessible_client(conn, client_id, user, "manage_work")
        storage_key = f"clients/{client['organization_id']}/{uuid4()}-{_safe_filename(file_name)}"

        try:
            storage.put_object(storage_key, content, content_type)
        except StorageNotConfiguredError as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        except StorageOperationError as error:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

        file_id = files_repo.create_file(
            conn,
            client["organization_id"],
            file_name,
            content_type,
            len(content),
            visibility,
            storage_key,
            user.id,
        )
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "file.uploaded",
            {"client_id": str(client_id), "file_id": str(file_id), "file_name": file_name, "size_bytes": len(content)},
        )

    return list_files(client_id, user)


def request_download(client_id: UUID, file_id: UUID, user: CurrentUserResponse) -> ClientFileDownloadResponse:
    is_admin = is_platform_admin(user)
    with connect() as conn:
        client = _accessible_client(conn, client_id, user)
        row = files_repo.get_file(conn, client["organization_id"], file_id)

    if not row or (not is_admin and row["visibility"] != "client"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado.")

    try:
        expires_in = 300
        url = storage.presigned_get_url(row["storage_key"], expires_in)
    except StorageNotConfiguredError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except StorageOperationError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

    return ClientFileDownloadResponse(url=url, expires_in=expires_in)


def delete_file(client_id: UUID, file_id: UUID, user: CurrentUserResponse) -> list[ClientFileSummary]:
    with connect() as conn:
        client = _accessible_client(conn, client_id, user, "manage_work")
        row = files_repo.get_file(conn, client["organization_id"], file_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado.")

        try:
            storage.delete_object(row["storage_key"])
        except StorageNotConfiguredError as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        except StorageOperationError as error:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

        files_repo.delete_file(conn, client["organization_id"], file_id)
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "file.deleted",
            {"client_id": str(client_id), "file_id": str(file_id), "file_name": row["file_name"]},
        )

    return list_files(client_id, user)


def _safe_filename(file_name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", file_name).strip("-")
    return normalized or "arquivo"


def _accessible_client(conn, client_id: UUID, user: CurrentUserResponse, capability: str | None = None):
    # Todo o módulo de arquivos fica atrás do gate "files" para client_user.
    return resolve_accessible_client(conn, client_id, user, module="files", capability=capability)
