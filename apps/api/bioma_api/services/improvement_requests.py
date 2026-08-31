"""Requisições de melhoria: da fila do copiloto para o trabalho de verdade.

Fecha o "Caminho B": quando o copiloto percebe uma necessidade que o catálogo
atual não atende, ele registra aqui com evidência. Aprovar **converte em
tarefa** — não duplica: a fila é caixa de entrada, a tarefa é o trabalho.

A visibilidade da tarefa criada segue `client_deliverable`:
- entrega que o cliente espera (ex.: o calendário de visitas dos representantes
  da Univet) nasce visível no board dele;
- melhoria interna de plataforma nasce escondida.
"""

from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_platform_admin
from bioma_api.db import connect
from bioma_api.repositories import improvement_requests as repo
from bioma_api.repositories import tasks as tasks_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.improvement_requests import (
    ImprovementRequest,
    ImprovementRequestConvert,
    ImprovementRequestCreate,
    ImprovementRequestReject,
)


def create_request(
    payload: ImprovementRequestCreate,
    user: CurrentUserResponse,
    proposed_by_agent: bool = False,
) -> ImprovementRequest:
    require_platform_admin(user)
    with connect() as conn:
        row = repo.create(
            conn,
            {
                "workspace_id": payload.workspace_id,
                "title": payload.title,
                "need": payload.need,
                "evidence": payload.evidence,
                "client_deliverable": payload.client_deliverable,
                # NULL marca "proposta pelo copiloto" — a tela mostra a origem.
                "proposed_by": None if proposed_by_agent else user.id,
            },
        )
    return ImprovementRequest(**row)


def list_requests(
    request_status: str | None, workspace_id: UUID | None, user: CurrentUserResponse
) -> list[ImprovementRequest]:
    require_platform_admin(user)
    with connect() as conn:
        rows = repo.list_requests(conn, request_status, workspace_id)
    return [ImprovementRequest(**row) for row in rows]


def convert_to_task(
    request_id: UUID, payload: ImprovementRequestConvert, user: CurrentUserResponse
) -> ImprovementRequest:
    require_platform_admin(user)

    with connect() as conn:
        request = repo.get(conn, request_id)
        if not request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisição não encontrada.")
        if request["status"] != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Requisição já revisada — converter de novo criaria uma tarefa duplicada.",
            )

        context = tasks_repo.find_list_context(conn, payload.list_id, is_platform_admin(user), user.id)
        if not context:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lista de tarefas não encontrada.")

        description = request["need"]
        if request["evidence"]:
            description = f"{description}\n\n**Evidência levantada pelo copiloto:**\n{request['evidence']}"

        task = tasks_repo.create_task(
            conn,
            payload.list_id,
            {
                "title": request["title"],
                "description": description,
                "status": "pending",
                "group_status": "NOT_STARTED",
                "due_date": payload.due_date,
                "owner_id": payload.owner_id,
                # É aqui que a decisão sobre o board do cliente se materializa.
                "client_visible": request["client_deliverable"],
            },
        )
        converted = repo.mark_converted(conn, request_id, task["id"], user.id, payload.review_note)
        if not converted:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Requisição já revisada.")
    return ImprovementRequest(**converted)


def reject_request(
    request_id: UUID, payload: ImprovementRequestReject, user: CurrentUserResponse
) -> ImprovementRequest:
    require_platform_admin(user)
    with connect() as conn:
        rejected = repo.reject(conn, request_id, user.id, payload.review_note)
        if not rejected:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Requisição não encontrada ou já revisada.",
            )
    return ImprovementRequest(**rejected)
