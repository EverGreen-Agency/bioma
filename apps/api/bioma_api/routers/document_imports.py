from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.document_imports import ProjectDocumentImport, ProjectDocumentImportMaterialize
from bioma_api.services import document_imports as service


router = APIRouter(tags=["project-document-imports"])


@router.get("/projects/{project_id}/document-imports", response_model=list[ProjectDocumentImport])
def list_imports(
    project_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[ProjectDocumentImport]:
    return service.list_imports(project_id, user)


@router.post(
    "/projects/{project_id}/document-imports",
    response_model=ProjectDocumentImport,
    status_code=status.HTTP_201_CREATED,
)
async def preview_import(
    project_id: UUID,
    file: UploadFile = File(...),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ProjectDocumentImport:
    content = await file.read(service.MAX_HTML_BYTES + 1)
    content_type = (file.content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    return service.preview_import(
        project_id, file.filename or "documento.html", content_type, content, user,
    )


@router.post("/project-document-imports/{import_id}/materialize", response_model=ProjectDocumentImport)
def materialize_import(
    import_id: UUID,
    payload: ProjectDocumentImportMaterialize,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ProjectDocumentImport:
    return service.materialize_import(import_id, payload, user)
