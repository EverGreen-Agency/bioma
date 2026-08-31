from uuid import UUID

from fastapi import APIRouter, Depends, Query

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.content_intelligence import (
    ContentRetrospectiveSummary,
    ContentScriptSummary,
    GenerateRetrospectiveRequest,
    GenerateScriptsRequest,
    HookAnalysisSummary,
    InstagramPostSummary,
    ScriptScoreboard,
    LinkPostToScriptRequest,
    ScriptUpdateRequest,
)
from bioma_api.services import content_intelligence as service

router = APIRouter(prefix="/workspaces/{workspace_id}/content", tags=["content-intelligence"])


@router.get("/instagram-posts", response_model=list[InstagramPostSummary])
def list_instagram_posts(
    workspace_id: UUID,
    days: int = Query(default=90, ge=7, le=365),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[InstagramPostSummary]:
    return service.list_instagram_posts(workspace_id, user, days)


@router.get("/hook-bank", response_model=list[HookAnalysisSummary])
def list_hook_bank(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[HookAnalysisSummary]:
    return service.list_hook_bank(workspace_id, user)


@router.get("/retrospective", response_model=ContentRetrospectiveSummary | None)
def get_latest_retrospective(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ContentRetrospectiveSummary | None:
    return service.list_retrospectives(workspace_id, user)


@router.post("/retrospective", response_model=ContentRetrospectiveSummary, status_code=201)
def generate_retrospective(
    workspace_id: UUID,
    payload: GenerateRetrospectiveRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ContentRetrospectiveSummary:
    return service.generate_retrospective(workspace_id, user, payload.period_days)


@router.get("/script-scoreboard", response_model=ScriptScoreboard)
def get_script_scoreboard(
    workspace_id: UUID,
    period_days: int = 90,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ScriptScoreboard:
    """Os roteiros da IA performaram acima ou abaixo do resto da conta?"""
    return service.get_script_scoreboard(workspace_id, user, period_days)


@router.get("/scripts", response_model=list[ContentScriptSummary])
def list_scripts(
    workspace_id: UUID,
    status_filter: str | None = Query(default=None, alias="status"),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[ContentScriptSummary]:
    return service.list_scripts(workspace_id, user, status_filter)


@router.post("/scripts", response_model=list[ContentScriptSummary], status_code=201)
def generate_scripts(
    workspace_id: UUID,
    payload: GenerateScriptsRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[ContentScriptSummary]:
    return service.generate_scripts(workspace_id, user, payload)


@router.patch("/scripts/{script_id}", response_model=ContentScriptSummary)
def update_script(
    workspace_id: UUID,
    script_id: UUID,
    payload: ScriptUpdateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ContentScriptSummary:
    return service.update_script(workspace_id, script_id, user, payload.status, payload.scheduled_for)


@router.post("/instagram-posts/{post_id}/link-script", response_model=InstagramPostSummary)
def link_post_to_script(
    workspace_id: UUID,
    post_id: UUID,
    payload: LinkPostToScriptRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> InstagramPostSummary:
    return service.link_post_to_script(workspace_id, post_id, payload.script_id, user)
