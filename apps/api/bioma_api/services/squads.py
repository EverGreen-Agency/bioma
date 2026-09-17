import sys
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_client_module, require_workspace_capability
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import squads as squads_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.squads import (
    FinOpsSummaryResponse,
    RunSquadPayload,
    SquadDefinitionPayload,
    SquadDefinitionSummary,
    SquadExecutionSummary,
)
from bioma_api.worker_bridge import execute_squad_pipeline_safe


def list_squads(workspace_id: UUID, user: CurrentUserResponse) -> list[SquadDefinitionSummary]:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        rows = squads_repo.list_squad_definitions(conn, client["workspace_id"])
    return [SquadDefinitionSummary(**row) for row in rows]


def upsert_squad(
    workspace_id: UUID,
    payload: SquadDefinitionPayload,
    user: CurrentUserResponse,
) -> SquadDefinitionSummary:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user, "manage_config")
        row = squads_repo.upsert_squad_definition(conn, client["workspace_id"], payload.model_dump())
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "squad.definition_saved",
            {
                "workspace_id": str(client["workspace_id"]),
                "squad_slug": payload.squad_slug,
                "pilar": payload.pilar,
            },
        )
    return SquadDefinitionSummary(**row)


def run_squad(
    workspace_id: UUID,
    payload: RunSquadPayload,
    user: CurrentUserResponse,
) -> SquadExecutionSummary:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user, "generate_content")
        squad_def = squads_repo.get_squad_definition(conn, client["workspace_id"], payload.squad_slug)
        squad_id = squad_def["id"] if squad_def else None
        resolved_workspace_id = client["workspace_id"]
        organization_id = client["organization_id"]

    # Chamadas externas não mantêm a transação do banco aberta.
    result = execute_squad_pipeline_safe(
        pilar=payload.pilar,
        squad_key=squad_def["squad_slug"] if squad_def else payload.squad_slug,
        input_context=payload.input_data,
        requested_by_user_id=str(user.id),
    )

    with connect() as conn:
        execution_row = squads_repo.create_execution(
            conn,
            resolved_workspace_id,
            {
                "squad_id": squad_id,
                "pilar": payload.pilar,
                "squad_name": payload.squad_name,
                "triggered_by": user.email,
                "status": "completed",
                "generation_mode": result["generation_mode"],
                "input_data": payload.input_data,
                "output_data": result["output_data"],
                "token_usage": result["token_usage"],
                "estimated_cost_cents": result["estimated_cost_cents"],
                "execution_logs": result["execution_logs"],
                "completed_at": result["completed_at"],
            },
        )

        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "squad.pipeline_executed",
            {
                "workspace_id": str(resolved_workspace_id),
                "pilar": payload.pilar,
                "squad_slug": payload.squad_slug,
                "generation_mode": result["generation_mode"],
                "estimated_cost_cents": result["estimated_cost_cents"],
            },
        )

    return SquadExecutionSummary(**execution_row)


def list_executions(workspace_id: UUID, user: CurrentUserResponse, limit: int = 50) -> list[SquadExecutionSummary]:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        rows = squads_repo.list_executions(conn, client["workspace_id"], limit)
    return [SquadExecutionSummary(**row) for row in rows]


def get_finops(workspace_id: UUID, user: CurrentUserResponse) -> FinOpsSummaryResponse:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        totals = squads_repo.get_finops_summary(conn, client["workspace_id"])
    return FinOpsSummaryResponse(workspace_id=client["workspace_id"], **totals)


def _accessible_workspace(conn, workspace_id: UUID, user: CurrentUserResponse, capability: str | None = None):
    client = workspaces_repo.find_accessible_client(conn, workspace_id, is_platform_admin(user), user.id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
    require_client_module(client, user, "commercial")
    if capability:
        require_workspace_capability(client, user, capability)
    return client
