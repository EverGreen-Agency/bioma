from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.copilot import (
    CopilotAttachment,
    CopilotCommand,
    CopilotPlan,
    CopilotPlanRequest,
    CopilotRequest,
    CopilotResponse,
    CopilotRunTrace,
    CopilotThreadSummary,
    CopilotUsageSummary,
)
from bioma_api.services import copilot as service
from bioma_api.services import copilot_attachments as attachments_service
from bioma_api.services import copilot_plans as plans_service
from bioma_api.services import copilot_traces as traces_service

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.get("/commands", response_model=list[CopilotCommand])
def list_commands(
    surface: str = Query(default="workspace"),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[CopilotCommand]:
    """Alimenta o menu de `/` — o front nunca inventa comando."""
    from bioma_api.access import require_platform_admin

    require_platform_admin(user)
    return [CopilotCommand(**item) for item in service.catalog_for(surface, user)]


@router.post("", response_model=CopilotResponse)
def run_copilot(
    payload: CopilotRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> CopilotResponse:
    """Interpreta a mensagem, responde com fontes e executa só o reversível."""
    return service.run(payload, user)


# ------------------------------------------------------------- anexos


@router.post("/attachments", response_model=CopilotAttachment, status_code=201)
def upload_attachment(
    file: UploadFile = File(...),
    thread_id: UUID | None = Form(default=None),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> CopilotAttachment:
    """Anexa imagem, áudio ou documento. Extrai o texto na hora, quando dá.

    Extrair no upload (e não no envio) faz o usuário descobrir agora que o PDF
    é escaneado — em vez de perguntar algo sobre ele e receber resposta vaga.
    """
    return attachments_service.upload(file, thread_id, user)


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> dict[str, str]:
    return attachments_service.download_url(attachment_id, user)


@router.delete("/attachments/{attachment_id}")
def delete_attachment(
    attachment_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> dict[str, str]:
    return attachments_service.remove(attachment_id, user)


# ------------------------------------------------- conversas e auditoria


@router.get("/threads", response_model=list[CopilotThreadSummary])
def list_threads(
    status: str = Query(default="active", pattern="^(active|archived)$"),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[CopilotThreadSummary]:
    """Conversas do próprio usuário — alimenta a lista lateral do painel."""
    return traces_service.list_threads(status, user)


@router.get("/threads/{thread_id}", response_model=list[CopilotRunTrace])
def get_thread(
    thread_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[CopilotRunTrace]:
    """Turnos da conversa, cada um com a trilha completa da execução."""
    return traces_service.get_thread_runs(thread_id, user)


@router.post("/threads/{thread_id}/archive", response_model=CopilotThreadSummary)
def archive_thread(
    thread_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> CopilotThreadSummary:
    return traces_service.archive_thread(thread_id, user)


@router.get("/runs/{run_id}", response_model=CopilotRunTrace)
def get_run(
    run_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> CopilotRunTrace:
    """Auditoria de uma execução: etapas, fontes, memória, token, custo, tempo."""
    return traces_service.get_run(run_id, user)


@router.get("/usage", response_model=CopilotUsageSummary)
def usage(
    days: int = Query(default=30, ge=1, le=365),
    mine_only: bool = Query(default=False),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> CopilotUsageSummary:
    """Consumo do copiloto na janela — token, custo e tempo médio."""
    return traces_service.usage(days, mine_only, user)


# ---------------------------------------------------------------- planos


@router.post("/plans", response_model=CopilotPlan, status_code=201)
def create_plan(
    payload: CopilotPlanRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> CopilotPlan:
    """Monta um plano de N etapas a partir de um objetivo. NÃO executa nada."""
    return plans_service.create_plan(payload, user)


@router.get("/plans", response_model=list[CopilotPlan])
def list_plans(
    workspace_id: str | None = Query(default=None),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[CopilotPlan]:
    from uuid import UUID

    return plans_service.list_plans(UUID(workspace_id) if workspace_id else None, user)


@router.get("/plans/{plan_id}", response_model=CopilotPlan)
def get_plan(
    plan_id: str,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> CopilotPlan:
    from uuid import UUID

    return plans_service.get_plan(UUID(plan_id), user)


@router.post("/plans/{plan_id}/approve", response_model=CopilotPlan)
def approve_plan(
    plan_id: str,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> CopilotPlan:
    """Aprova e executa as etapas reversíveis. As visíveis ao cliente continuam
    bloqueadas, aguardando confirmação individual."""
    from uuid import UUID

    return plans_service.approve_and_run(UUID(plan_id), user)


@router.post("/plans/{plan_id}/reject", response_model=CopilotPlan)
def reject_plan(
    plan_id: str,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> CopilotPlan:
    from uuid import UUID

    return plans_service.reject_plan(UUID(plan_id), user)


@router.post("/plans/{plan_id}/steps/{step_id}/confirm", response_model=CopilotPlan)
def confirm_step(
    plan_id: str,
    step_id: str,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> CopilotPlan:
    """Confirma individualmente uma etapa visível ao cliente."""
    from uuid import UUID

    return plans_service.confirm_step(UUID(plan_id), UUID(step_id), user)
