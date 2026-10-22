import json
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import resolve_accessible_client
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories.prospecting import prospecting_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.prospecting import (
    CreateProspectingListRequest,
    ProspectingCockpitContextResponse,
    ProspectingListDetailResponse,
    ProspectingListItemResponse,
    ProspectingListSummaryResponse,
    ProspectingSessionResponse,
    RecordDispositionRequest,
    SalesKnowledgeCardResponse,
    SalesKnowledgeCardStatusUpdate,
    StartProspectingSessionRequest,
)


def list_knowledge_cards(
    workspace_id: UUID,
    user: CurrentUserResponse,
    query: str | None = None,
    motion: str | None = None,
    card_type: str | None = None,
    status_filter: str | None = None,
) -> list[SalesKnowledgeCardResponse]:
    with connect() as conn:
        resolve_accessible_client(conn, workspace_id, user, module="hub", capability="view")
        rows = prospecting_repo.list_knowledge_cards(
            conn,
            workspace_id=workspace_id,
            query=query,
            motion=motion,
            card_type=card_type,
            status=status_filter,
        )
        return [SalesKnowledgeCardResponse(**r) for r in rows]


def update_knowledge_card_status(
    workspace_id: UUID,
    card_id: UUID,
    payload: SalesKnowledgeCardStatusUpdate,
    user: CurrentUserResponse,
) -> SalesKnowledgeCardResponse:
    with connect() as conn:
        resolve_accessible_client(conn, workspace_id, user, module="hub", capability="manage")
        updated = prospecting_repo.update_card_status(conn, card_id, payload.status)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Card de conhecimento não encontrada.",
            )
        return SalesKnowledgeCardResponse(**updated)


def create_prospecting_list(
    workspace_id: UUID,
    payload: CreateProspectingListRequest,
    user: CurrentUserResponse,
) -> ProspectingListSummaryResponse:
    with connect() as conn:
        workspace = resolve_accessible_client(conn, workspace_id, user, module="hub", capability="manage")
        ws_row = conn.execute(
            "select tenant_organization_id from workspaces where id = %s",
            (workspace["workspace_id"],),
        ).fetchone()
        if not ws_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")

        items_dict = [it.model_dump() for it in payload.items]
        created = prospecting_repo.create_prospecting_list(
            conn,
            workspace_id=workspace["workspace_id"],
            tenant_org_id=ws_row["tenant_organization_id"],
            title=payload.title,
            source=payload.source,
            segment=payload.segment,
            target_region=payload.target_region,
            filters=payload.filters,
            user_id=user.id,
            items=items_dict,
        )

        client_hub_repo.write_audit(
            conn,
            user.id,
            workspace["workspace_id"],
            "prospecting.list_created",
            {
                "list_id": str(created["id"]),
                "title": payload.title,
                "total_leads": len(items_dict),
            },
        )

        return ProspectingListSummaryResponse(**created)


def list_prospecting_lists(
    workspace_id: UUID,
    user: CurrentUserResponse,
) -> list[ProspectingListSummaryResponse]:
    with connect() as conn:
        workspace = resolve_accessible_client(conn, workspace_id, user, module="hub", capability="view")
        rows = prospecting_repo.list_prospecting_lists(conn, workspace["workspace_id"])
        return [ProspectingListSummaryResponse(**r) for r in rows]


def get_prospecting_list(
    workspace_id: UUID,
    list_id: UUID,
    user: CurrentUserResponse,
) -> ProspectingListDetailResponse:
    with connect() as conn:
        resolve_accessible_client(conn, workspace_id, user, module="hub", capability="view")
        detail = prospecting_repo.get_prospecting_list_detail(conn, list_id)
        if not detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lista de prospecção não encontrada.",
            )
        return ProspectingListDetailResponse(**detail)


def start_prospecting_session(
    workspace_id: UUID,
    payload: StartProspectingSessionRequest,
    user: CurrentUserResponse,
) -> ProspectingSessionResponse:
    with connect() as conn:
        workspace = resolve_accessible_client(conn, workspace_id, user, module="hub", capability="manage")
        created = prospecting_repo.create_session(
            conn,
            workspace_id=workspace["workspace_id"],
            user_id=user.id,
            list_id=payload.list_id,
            motion=payload.motion,
            target_calls=payload.target_calls,
        )
        full_session = prospecting_repo.get_session(conn, created["id"])
        if not full_session:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao criar sessão.")
        return ProspectingSessionResponse(**full_session)


def get_session_cockpit(
    workspace_id: UUID,
    session_id: UUID,
    user: CurrentUserResponse,
) -> ProspectingCockpitContextResponse:
    with connect() as conn:
        resolve_accessible_client(conn, workspace_id, user, module="hub", capability="view")
        session_data = prospecting_repo.get_session(conn, session_id)
        if not session_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessão não encontrada.")

        items = [ProspectingListItemResponse(**it) for it in session_data.get("items", [])]
        pending_items = [it for it in items if it.status == "pending"]
        current_item = pending_items[0] if pending_items else None

        cards = prospecting_repo.list_knowledge_cards(
            conn,
            workspace_id=workspace_id,
            motion=session_data.get("motion"),
        )

        return ProspectingCockpitContextResponse(
            session=ProspectingSessionResponse(**session_data),
            current_item=current_item,
            queue_remaining=len(pending_items),
            cards=[SalesKnowledgeCardResponse(**c) for c in cards],
        )


def record_session_disposition(
    workspace_id: UUID,
    session_id: UUID,
    payload: RecordDispositionRequest,
    user: CurrentUserResponse,
) -> ProspectingCockpitContextResponse:
    with connect() as conn:
        workspace = resolve_accessible_client(conn, workspace_id, user, module="hub", capability="manage")

        handoff_dict = payload.handoff.model_dump() if payload.handoff else None

        result = prospecting_repo.record_disposition(
            conn,
            session_id=session_id,
            item_id=payload.item_id,
            disposition=payload.disposition,
            notes=payload.notes,
            scheduled_follow_up_at=payload.scheduled_follow_up_at,
            handoff_payload=handoff_dict,
        )

        # Se Reunião Agendada, orquestra criação da oportunidade e sessão preparatória para o Closer
        if payload.disposition == "meeting_scheduled" and payload.handoff:
            item_data = result.get("item")
            company_name = item_data["company_name"] if item_data else "Prospect Qualificado"
            contact_name = item_data.get("contact_name") if item_data else None

            # 1. Registra no CRM / Leads
            conn.execute(
                """
                insert into leads (
                    organization_id, name, company, email, phone, stage, notes, source
                ) values (%s, %s, %s, %s, %s, 'meeting', %s, 'prospecting_session')
                """,
                (
                    workspace["tenant_organization_id"] if "tenant_organization_id" in workspace else workspace["workspace_id"],
                    contact_name or company_name,
                    company_name,
                    item_data.get("email") if item_data else None,
                    item_data.get("phone") if item_data else None,
                    f"Dor: {payload.handoff.problem}\nImpacto: {payload.handoff.impact}\nData: {payload.handoff.meeting_at}\nNotas: {payload.handoff.closer_notes or ''}",
                ),
            )

            # 2. Registra na tabela de Oportunidades do Radar
            conn.execute(
                """
                insert into opportunity_radar (
                    workspace_id, owner_user_id, source_platform, external_id, title, description,
                    fit_score, fit_analysis, status
                ) values (%s, %s, 'sales_prospecting_os', %s, %s, %s, 90, %s, 'lead_converted')
                """,
                (
                    workspace["workspace_id"],
                    user.id,
                    str(payload.item_id),
                    f"Reunião Qualificada: {company_name}",
                    f"Dor: {payload.handoff.problem}\nImpacto: {payload.handoff.impact}\nData Agendada: {payload.handoff.meeting_at}",
                    json.dumps({
                        "motion": payload.handoff.motion,
                        "problem": payload.handoff.problem,
                        "impact": payload.handoff.impact,
                        "scheduled_at": payload.handoff.meeting_at,
                    }),
                ),
            )

            client_hub_repo.write_audit(
                conn,
                user.id,
                workspace["workspace_id"],
                "prospecting.meeting_scheduled",
                {
                    "item_id": str(payload.item_id),
                    "company_name": company_name,
                    "handoff": handoff_dict,
                },
            )

    return get_session_cockpit(workspace_id, session_id, user)


def finish_session(
    workspace_id: UUID,
    session_id: UUID,
    user: CurrentUserResponse,
) -> ProspectingSessionResponse:
    with connect() as conn:
        resolve_accessible_client(conn, workspace_id, user, module="hub", capability="manage")
        finished = prospecting_repo.finish_session(conn, session_id)
        if not finished:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessão não encontrada.")
        full = prospecting_repo.get_session(conn, session_id)
        return ProspectingSessionResponse(**(full or finished))
