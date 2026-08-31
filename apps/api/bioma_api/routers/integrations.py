"""Status real das integrações de ambiente (sem mock).

Expõe apenas flags booleanas de configuração — nunca os valores das
credenciais. EG admin only: alimenta a aba Integrações das Configurações.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from bioma_api.access import require_platform_admin
from bioma_api.auth import current_user_from_request
from bioma_api.config import get_settings
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.github import (
    GitHubConnectionInput,
    GitHubConnectionSummary,
    GitHubActivitySyncRequest,
    GitHubActivitySyncResult,
    GitHubIssueCreateRequest,
    GitHubIssueLinkSummary,
    GitHubCompletionSuggestions,
    GitHubProjectActivity,
)
from bioma_api.services import github as github_service
from bioma_api.services import kommo as kommo_service

router = APIRouter(prefix="/integrations", tags=["integrations"])


class IntegrationsStatusResponse(BaseModel):
    github_token_configured: bool
    storage_configured: bool
    google_oauth_configured: bool
    app_env: str
    # QUAIS variáveis faltam, não só "faltou alguma".
    #
    # Motivo: "Não Configurado" manda a pessoa conferir três variáveis numa
    # aba de deploy sem dizer qual está ausente — e no Railway, onde API e
    # worker são serviços com conjuntos de variáveis SEPARADOS, o caso comum é
    # a variável existir (no worker) e faltar exatamente aqui. Nomear a que
    # falta transforma uma caça de meia hora em cinco segundos.
    #
    # Só nome de variável, nunca valor: isto responde para EG admin, mas
    # devolver segredo por engano é o tipo de vazamento que não se desfaz.
    storage_missing_vars: list[str] = []
    google_oauth_missing_vars: list[str] = []


@router.get("/status", response_model=IntegrationsStatusResponse)
def get_status(user: CurrentUserResponse = Depends(current_user_from_request)) -> IntegrationsStatusResponse:
    require_platform_admin(user)
    settings = get_settings()

    storage_missing = [
        name
        for name, value in (
            ("STORAGE_S3_BUCKET", settings.storage_s3_bucket),
            ("STORAGE_S3_ACCESS_KEY_ID", settings.storage_s3_access_key_id),
            ("STORAGE_S3_SECRET_ACCESS_KEY", settings.storage_s3_secret_access_key),
        )
        if not value
    ]
    oauth_missing = [
        name
        for name, value in (
            ("GOOGLE_OAUTH_CLIENT_ID", settings.google_oauth_client_id),
            ("GOOGLE_OAUTH_CLIENT_SECRET", settings.google_oauth_client_secret),
        )
        if not value
    ]

    return IntegrationsStatusResponse(
        github_token_configured=bool(settings.github_api_token),
        storage_configured=settings.storage_configured,
        google_oauth_configured=settings.google_oauth_configured,
        app_env=settings.app_env,
        storage_missing_vars=storage_missing,
        google_oauth_missing_vars=oauth_missing,
    )


class KommoConfigInput(BaseModel):
    client_id: str
    client_secret: str
    access_token: str
    subdomain: str


class KommoConfigResponse(BaseModel):
    configured: bool
    subdomain: str | None


@router.get("/{organization_id}/kommo", response_model=KommoConfigResponse)
def get_kommo_config(
    organization_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> KommoConfigResponse:
    return KommoConfigResponse(**kommo_service.get_config(user, organization_id))


@router.post("/{organization_id}/kommo")
def setup_kommo_config(
    organization_id: UUID,
    payload: KommoConfigInput,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> dict[str, str]:
    kommo_service.save_config(
        user,
        organization_id,
        payload.client_id,
        payload.client_secret,
        payload.access_token,
        payload.subdomain,
    )
    return {"status": "ok"}


@router.get("/github/projects/{project_id}", response_model=GitHubConnectionSummary)
def get_github_connection(
    project_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> GitHubConnectionSummary:
    return github_service.get_connection(project_id, user)


@router.put("/github/projects/{project_id}", response_model=GitHubConnectionSummary)
def upsert_github_connection(
    project_id: UUID,
    payload: GitHubConnectionInput,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> GitHubConnectionSummary:
    return github_service.upsert_connection(project_id, payload, user)


@router.get("/github/projects/{project_id}/activity", response_model=GitHubProjectActivity)
def get_github_activity(
    project_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> GitHubProjectActivity:
    return github_service.get_activity(project_id, user, limit)


@router.post(
    "/github/projects/{project_id}/publish-update",
    response_model=GitHubActivitySyncResult,
)
def publish_github_activity_update(
    project_id: UUID,
    payload: GitHubActivitySyncRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> GitHubActivitySyncResult:
    return github_service.publish_activity_update(project_id, payload, user)


@router.post("/github/deliverables/{deliverable_id}/issue", response_model=GitHubIssueLinkSummary)
def create_github_issue(
    deliverable_id: UUID,
    payload: GitHubIssueCreateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> GitHubIssueLinkSummary:
    return github_service.create_issue_from_deliverable(deliverable_id, payload, user)


@router.get(
    "/github/projects/{project_id}/completion-suggestions",
    response_model=GitHubCompletionSuggestions,
)
def github_completion_suggestions(
    project_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    """Entregas cuja issue fechou no GitHub mas que seguem abertas no Bioma.

    Sugere; não conclui. Concluir entrega tem efeito contratual e continua
    exigindo ação humana (decisão #9).
    """
    return github_service.list_completion_suggestions(project_id, user)
