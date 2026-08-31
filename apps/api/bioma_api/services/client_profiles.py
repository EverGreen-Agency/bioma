from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import resolve_accessible_client
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import client_profiles as profile_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.client_profile import (
    ClientProfilePayload,
    ClientProfileSectionProgress,
    ClientProfileSummary,
)


SECTION_FIELDS = {
    "basic": ("Informações básicas", ("sector", "primary_offer", "initial_objective")),
    "contact": ("Informações de contato", ("contact_email", "contact_phone", "website", "business_address")),
    "business": ("Detalhes do negócio", ("business_details", "target_audience", "competitors")),
    "marketing": ("Marketing e objetivos", ("marketing_objectives", "marketing_history", "challenges_opportunities")),
    "preferences": ("Recursos e preferências", ("resources_budget", "tone_of_voice", "preferences_restrictions")),
}


def get_profile(workspace_id: UUID, user: CurrentUserResponse) -> ClientProfileSummary:
    with connect() as conn:
        workspace = _workspace(conn, workspace_id, user, "view")
        row = profile_repo.get_profile(conn, workspace["workspace_id"])
    return _summary(workspace["workspace_id"], row)


def upsert_profile(
    workspace_id: UUID,
    payload: ClientProfilePayload,
    user: CurrentUserResponse,
) -> ClientProfileSummary:
    updates = _normalized_updates(payload.model_dump(exclude_unset=True))
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe ao menos um campo do contexto do cliente.",
        )
    with connect() as conn:
        workspace = _workspace(conn, workspace_id, user, "manage_work")
        row = profile_repo.upsert_profile(conn, workspace["workspace_id"], user.id, updates)
        client_hub_repo.write_audit(
            conn,
            user.id,
            workspace["organization_id"],
            "client_profile.updated",
            {"workspace_id": str(workspace["workspace_id"]), "fields": sorted(updates)},
        )
    return _summary(workspace["workspace_id"], row)


def planning_context(row) -> dict[str, str]:
    if not row:
        return {}
    return {
        key: value
        for key, value in dict(row).items()
        if key != "updated_at" and isinstance(value, str) and value.strip()
    }


def _workspace(conn, workspace_id: UUID, user: CurrentUserResponse, capability: str):
    workspace = resolve_accessible_client(
        conn,
        workspace_id,
        user,
        module="hub",
        capability=capability,
        require_kind="client",
    )
    return workspace


def _normalized_updates(payload: dict) -> dict:
    return {
        key: value.strip() if isinstance(value, str) else value
        for key, value in payload.items()
    }


def _summary(workspace_id: UUID, row) -> ClientProfileSummary:
    data = dict(row) if row else {}
    total = sum(len(fields) for _, fields in SECTION_FIELDS.values())
    filled_total = 0
    sections = []
    for key, (label, fields) in SECTION_FIELDS.items():
        filled = sum(1 for field in fields if isinstance(data.get(field), str) and data[field].strip())
        filled_total += filled
        sections.append(
            ClientProfileSectionProgress(
                key=key,
                label=label,
                filled=filled,
                total=len(fields),
                percentage=round(filled / len(fields) * 100),
            )
        )
    return ClientProfileSummary(
        workspace_id=workspace_id,
        completion_percentage=round(filled_total / total * 100) if total else 0,
        sections=sections,
        **{key: data.get(key) for key in ClientProfilePayload.model_fields},
        updated_at=data.get("updated_at"),
    )
