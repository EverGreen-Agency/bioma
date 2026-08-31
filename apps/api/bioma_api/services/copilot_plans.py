"""Planos multi-etapa do copiloto — monta, aprova, executa.

A ponte que faltava: o copiloto executava uma ação por mensagem; os casos reais
("cadastrar cliente novo", "roteiro dos próximos anúncios", "hackathon X") são
sequências de 4-8 ações dependentes.

Contrato de segurança (estende o que já valia para ação avulsa):
- plano nasce `pending_approval` e **nada roda antes da aprovação** — nem etapa
  reversível. Aprovar o plano é aprovar a sequência;
- etapa cuja ação é visível ao cliente fica `blocked` mesmo com plano aprovado:
  ela exige confirmação própria (é a decisão do Eduardo, aplicada por etapa);
- primeira falha interrompe: o resto vira `skipped`. Meio-plano executado sem
  aviso é pior que plano não executado.
"""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import require_platform_admin
from bioma_api.db import connect
from bioma_api.repositories import copilot_plans as repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.copilot import CopilotPlan, CopilotPlanRequest, CopilotPlanStep
from bioma_api.services import copilot as copilot_service
from bioma_api.worker_bridge import copilot_action_catalog, copilot_plan_multistep_safe


def create_plan(payload: CopilotPlanRequest, user: CurrentUserResponse) -> CopilotPlan:
    require_platform_admin(user)
    catalog = copilot_action_catalog()

    # Reaproveita o dossiê do copiloto avulso: mesmo contexto, mesma memória,
    # mesmas skills aprovadas — o planejador não vive num universo paralelo.
    dossier_payload = CopilotPlanContext(payload.workspace_id)
    dossier, context, _ = copilot_service._build_dossier(dossier_payload, user)

    allowed = copilot_service.SURFACE_ACTIONS.get("workspace", []) + [
        name for name in catalog if name not in copilot_service.SURFACE_ACTIONS.get("workspace", [])
    ]

    try:
        result = copilot_plan_multistep_safe(
            {
                "goal": payload.goal,
                "context": context,
                "dossier": dossier,
                "allowed_actions": allowed,
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="O copiloto não conseguiu montar o plano agora. Tente novamente.",
        ) from exc

    output = result["output"]
    raw_steps = output.get("steps", [])[:10]

    valid_steps: list[dict] = []
    for raw in raw_steps:
        action_name = raw.get("action")
        spec = catalog.get(action_name)
        if not spec:
            # Nome fora do catálogo: descartado, nunca gravado como etapa.
            continue
        try:
            params = json.loads(raw.get("params") or "{}")
        except json.JSONDecodeError:
            params = {}
        if not isinstance(params, dict):
            params = {}
        valid_steps.append(
            {
                "action_name": action_name,
                "label": raw.get("label") or spec["label"],
                "params": params,
                "why": raw.get("why", ""),
                # Ação visível ao cliente nasce bloqueada: aprovar o plano não
                # basta para ela.
                "status": "pending" if spec["reversible"] else "blocked",
            }
        )

    requires_confirmation = sum(1 for step in valid_steps if step["status"] == "blocked")

    with connect() as conn:
        plan_row = repo.create_plan(
            conn,
            {
                "workspace_id": payload.workspace_id,
                "created_by": user.id,
                "goal": payload.goal,
                "summary": output.get("summary", ""),
                "requires_confirmation_count": requires_confirmation,
                "generation_mode": result["generation_mode"],
            },
        )
        for position, step in enumerate(valid_steps):
            repo.add_step(conn, plan_row["id"], position, step)
        steps = repo.list_steps(conn, plan_row["id"])

    return _plan(plan_row, steps, output.get("open_questions", []))


def list_plans(workspace_id: UUID | None, user: CurrentUserResponse) -> list[CopilotPlan]:
    require_platform_admin(user)
    with connect() as conn:
        rows = repo.list_plans(conn, workspace_id)
        return [_plan(row, repo.list_steps(conn, row["id"])) for row in rows]


def get_plan(plan_id: UUID, user: CurrentUserResponse) -> CopilotPlan:
    require_platform_admin(user)
    with connect() as conn:
        row = repo.get_plan(conn, plan_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano não encontrado.")
        steps = repo.list_steps(conn, plan_id)
    return _plan(row, steps)


def reject_plan(plan_id: UUID, user: CurrentUserResponse) -> CopilotPlan:
    require_platform_admin(user)
    with connect() as conn:
        row = repo.get_plan(conn, plan_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano não encontrado.")
        if row["status"] != "pending_approval":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Só plano pendente pode ser rejeitado.")
        updated = repo.set_plan_status(conn, plan_id, "rejected")
        steps = repo.list_steps(conn, plan_id)
    return _plan(updated, steps)


def approve_and_run(plan_id: UUID, user: CurrentUserResponse) -> CopilotPlan:
    """Aprova o plano e executa as etapas reversíveis, em ordem."""
    require_platform_admin(user)

    with connect() as conn:
        approved = repo.approve_plan(conn, plan_id, user.id)
        if not approved:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Plano não encontrado ou já aprovado — aprovar duas vezes reexecutaria as etapas.",
            )
        repo.set_plan_status(conn, plan_id, "running")
        steps = repo.list_steps(conn, plan_id)

    catalog = copilot_action_catalog()
    failed = False

    for step in steps:
        if step["status"] == "blocked":
            # Continua bloqueada: espera confirmação individual.
            continue
        if failed:
            with connect() as conn:
                repo.update_step(
                    conn, step["id"], {"status": "skipped", "detail": "Etapa anterior falhou; sequência interrompida."}
                )
            continue

        spec = catalog.get(step["action_name"])
        if not spec:
            with connect() as conn:
                repo.update_step(conn, step["id"], {"status": "failed", "detail": "Ação não existe mais no catálogo."})
            failed = True
            continue

        action = copilot_service._execute(
            step["action_name"], spec, step["params"], step["why"], None, user, None
        )
        with connect() as conn:
            repo.update_step(
                conn,
                step["id"],
                {
                    "status": "executed" if action.status == "executed" else "failed",
                    "detail": action.detail,
                    "undo_hint": action.undo_hint,
                },
            )
        if action.status != "executed":
            failed = True

    with connect() as conn:
        final_steps = repo.list_steps(conn, plan_id)
        blocked = [step for step in final_steps if step["status"] == "blocked"]
        if failed:
            final_status = "failed"
        elif blocked:
            # Ainda há etapa esperando confirmação — o plano não terminou.
            final_status = "approved"
        else:
            final_status = "completed"
        updated = repo.set_plan_status(
            conn, plan_id, final_status, "Uma ou mais etapas falharam." if failed else None
        )
        final_steps = repo.list_steps(conn, plan_id)
    return _plan(updated, final_steps)


def confirm_step(plan_id: UUID, step_id: UUID, user: CurrentUserResponse) -> CopilotPlan:
    """Confirma individualmente uma etapa visível ao cliente."""
    require_platform_admin(user)
    catalog = copilot_action_catalog()

    with connect() as conn:
        plan_row = repo.get_plan(conn, plan_id)
        if not plan_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano não encontrado.")
        if plan_row["status"] not in ("approved", "running"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Aprove o plano antes de confirmar etapas individuais.",
            )
        steps = repo.list_steps(conn, plan_id)

    step = next((item for item in steps if item["id"] == step_id), None)
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etapa não encontrada.")
    if step["status"] != "blocked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Esta etapa não está aguardando confirmação."
        )

    spec = catalog.get(step["action_name"])
    if not spec:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ação não existe mais no catálogo.")

    action = copilot_service._execute(
        step["action_name"], spec, step["params"], step["why"], None, user, plan_row["workspace_id"]
    )
    with connect() as conn:
        repo.update_step(
            conn,
            step_id,
            {
                "status": "executed" if action.status == "executed" else "failed",
                "detail": action.detail,
                "undo_hint": action.undo_hint,
            },
        )
        final_steps = repo.list_steps(conn, plan_id)
        pending = [item for item in final_steps if item["status"] in ("pending", "blocked", "running")]
        updated = repo.set_plan_status(conn, plan_id, "approved" if pending else "completed")
        final_steps = repo.list_steps(conn, plan_id)
    return _plan(updated, final_steps)


class CopilotPlanContext:
    """Adaptador mínimo para reusar `_build_dossier` sem duplicar o dossiê."""

    def __init__(self, workspace_id: UUID | None):
        self.surface = "workspace"
        self.task_id = None
        self.workspace_id = workspace_id


def _plan(row: dict, steps: list[dict], open_questions: list[str] | None = None) -> CopilotPlan:
    return CopilotPlan(
        id=row["id"],
        workspace_id=row["workspace_id"],
        goal=row["goal"],
        summary=row["summary"],
        status=row["status"],
        generation_mode=row["generation_mode"],
        requires_confirmation_count=row["requires_confirmation_count"],
        error_message=row["error_message"],
        steps=[
            CopilotPlanStep(
                id=step["id"],
                position=step["position"],
                action_name=step["action_name"],
                label=step["label"],
                params=step["params"],
                why=step["why"],
                status=step["status"],
                detail=step["detail"],
                undo_hint=step["undo_hint"],
            )
            for step in steps
        ],
        open_questions=open_questions or [],
    )
