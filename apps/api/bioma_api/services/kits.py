from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import require_platform_admin
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import kits as kits_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.kits import (
    KitDefinitionCreateRequest,
    KitDefinitionSummary,
    KitDefinitionUpdateRequest,
    KitPieceCreateRequest,
    KitPieceSummary,
    KitPieceUpdateRequest,
    KitShipmentCreateRequest,
    KitShipmentStatusUpdateRequest,
    KitShipmentSummary,
)


def _tenant_id(conn, user: CurrentUserResponse) -> UUID:
    tenant_id = workspaces_repo.find_platform_tenant_id(conn, user.id)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant administrativo não encontrado.")
    return tenant_id


def _with_total_cost(conn, tenant_id: UUID, row: dict) -> KitDefinitionSummary:
    pieces = row["pieces"] or []
    costs = kits_repo.piece_costs_by_id(conn, tenant_id, [entry["piece_id"] for entry in pieces])
    total = sum(costs.get(UUID(str(entry["piece_id"])), 0) * entry["quantity"] for entry in pieces)
    return KitDefinitionSummary(**row, total_cost_cents=total)


def list_pieces(user: CurrentUserResponse) -> list[KitPieceSummary]:
    require_platform_admin(user)
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        rows = kits_repo.list_pieces(conn, tenant_id)
    return [KitPieceSummary(**row) for row in rows]


def create_piece(payload: KitPieceCreateRequest, user: CurrentUserResponse) -> KitPieceSummary:
    require_platform_admin(user)
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        row = kits_repo.create_piece(conn, tenant_id, payload.model_dump())
        client_hub_repo.write_audit(conn, user.id, tenant_id, "kit_piece.created", {"piece_id": str(row["id"]), "name": row["name"]})
    return KitPieceSummary(**row)


def update_piece(piece_id: UUID, payload: KitPieceUpdateRequest, user: CurrentUserResponse) -> KitPieceSummary:
    require_platform_admin(user)
    updates = payload.model_dump(exclude_unset=True)
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        row = kits_repo.update_piece(conn, tenant_id, piece_id, updates)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Peça não encontrada.")
        client_hub_repo.write_audit(conn, user.id, tenant_id, "kit_piece.updated", {"piece_id": str(piece_id), "fields": sorted(updates)})
    return KitPieceSummary(**row)


def list_kit_definitions(user: CurrentUserResponse) -> list[KitDefinitionSummary]:
    require_platform_admin(user)
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        rows = kits_repo.list_kit_definitions(conn, tenant_id)
        return [_with_total_cost(conn, tenant_id, dict(row)) for row in rows]


def create_kit_definition(payload: KitDefinitionCreateRequest, user: CurrentUserResponse) -> KitDefinitionSummary:
    require_platform_admin(user)
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        _validate_pieces_exist(conn, tenant_id, payload.pieces)
        data = payload.model_dump()
        data["pieces"] = [{"piece_id": str(entry["piece_id"]), "quantity": entry["quantity"]} for entry in data["pieces"]]
        row = kits_repo.create_kit_definition(conn, tenant_id, data)
        client_hub_repo.write_audit(conn, user.id, tenant_id, "kit_definition.created", {"kit_definition_id": str(row["id"]), "name": row["name"]})
        return _with_total_cost(conn, tenant_id, dict(row))


def update_kit_definition(kit_definition_id: UUID, payload: KitDefinitionUpdateRequest, user: CurrentUserResponse) -> KitDefinitionSummary:
    require_platform_admin(user)
    updates = payload.model_dump(exclude_unset=True)
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        if "pieces" in updates and updates["pieces"] is not None:
            _validate_pieces_exist(conn, tenant_id, payload.pieces or [])
            updates["pieces"] = [{"piece_id": str(entry["piece_id"]), "quantity": entry["quantity"]} for entry in updates["pieces"]]
        row = kits_repo.update_kit_definition(conn, tenant_id, kit_definition_id, updates)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kit não encontrado.")
        client_hub_repo.write_audit(conn, user.id, tenant_id, "kit_definition.updated", {"kit_definition_id": str(kit_definition_id), "fields": sorted(updates)})
        return _with_total_cost(conn, tenant_id, dict(row))


def _validate_pieces_exist(conn, tenant_id: UUID, pieces) -> None:
    if not pieces:
        return
    costs = kits_repo.piece_costs_by_id(conn, tenant_id, [entry.piece_id for entry in pieces])
    missing = [str(entry.piece_id) for entry in pieces if entry.piece_id not in costs]
    if missing:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Peças não encontradas: {', '.join(missing)}.")


def create_shipment(payload: KitShipmentCreateRequest, user: CurrentUserResponse) -> KitShipmentSummary:
    require_platform_admin(user)
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        if not kits_repo.get_kit_definition(conn, tenant_id, payload.kit_definition_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kit não encontrado.")
        if not kits_repo.find_client_organization(conn, payload.client_id, tenant_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
        shipment_id = kits_repo.create_shipment(conn, payload.kit_definition_id, payload.client_id, user.id, payload.notes)
        client_hub_repo.write_audit(conn, user.id, tenant_id, "kit_shipment.created", {
            "shipment_id": str(shipment_id), "kit_definition_id": str(payload.kit_definition_id), "client_id": str(payload.client_id),
        })
        row = next(r for r in kits_repo.list_shipments(conn, tenant_id) if r["id"] == shipment_id)
    return KitShipmentSummary(**row)


def update_shipment_status(shipment_id: UUID, payload: KitShipmentStatusUpdateRequest, user: CurrentUserResponse) -> KitShipmentSummary:
    require_platform_admin(user)
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        updated = kits_repo.update_shipment_status(conn, tenant_id, shipment_id, payload.status, payload.notes)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Envio não encontrado.")
        client_hub_repo.write_audit(conn, user.id, tenant_id, "kit_shipment.status_updated", {"shipment_id": str(shipment_id), "status": payload.status})
        row = next(r for r in kits_repo.list_shipments(conn, tenant_id) if r["id"] == shipment_id)
    return KitShipmentSummary(**row)


def list_shipments(user: CurrentUserResponse, client_id: UUID | None = None) -> list[KitShipmentSummary]:
    require_platform_admin(user)
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        rows = kits_repo.list_shipments(conn, tenant_id, client_id)
    return [KitShipmentSummary(**row) for row in rows]
