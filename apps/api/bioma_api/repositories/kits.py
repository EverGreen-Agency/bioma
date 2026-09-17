from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb


def create_piece(conn, tenant_organization_id: UUID, payload: dict[str, Any]):
    return conn.execute(
        """
        insert into kit_pieces (tenant_organization_id, name, supplier, unit_cost_cents, stock_qty, image_url, status, metadata)
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        returning id, name, supplier, unit_cost_cents, stock_qty, image_url, status, metadata, created_at, updated_at
        """,
        (
            tenant_organization_id,
            payload["name"],
            payload.get("supplier"),
            payload.get("unit_cost_cents", 0),
            payload.get("stock_qty", 0),
            payload.get("image_url"),
            payload.get("status", "active"),
            Jsonb(payload.get("metadata", {})),
        ),
    ).fetchone()


def list_pieces(conn, tenant_organization_id: UUID):
    return conn.execute(
        """
        select id, name, supplier, unit_cost_cents, stock_qty, image_url, status, metadata, created_at, updated_at
        from kit_pieces
        where tenant_organization_id = %s
        order by status, name
        """,
        (tenant_organization_id,),
    ).fetchall()


def get_piece(conn, tenant_organization_id: UUID, piece_id: UUID):
    return conn.execute(
        """
        select id, name, supplier, unit_cost_cents, stock_qty, image_url, status, metadata, created_at, updated_at
        from kit_pieces
        where id = %s and tenant_organization_id = %s
        """,
        (piece_id, tenant_organization_id),
    ).fetchone()


def update_piece(conn, tenant_organization_id: UUID, piece_id: UUID, updates: dict[str, Any]):
    if not updates:
        return get_piece(conn, tenant_organization_id, piece_id)
    columns = []
    params: list[Any] = []
    for key, value in updates.items():
        columns.append(f"{key} = %s")
        params.append(Jsonb(value) if key == "metadata" else value)
    params.extend([piece_id, tenant_organization_id])
    return conn.execute(
        f"""
        update kit_pieces
        set {", ".join(columns)}, updated_at = now()
        where id = %s and tenant_organization_id = %s
        returning id, name, supplier, unit_cost_cents, stock_qty, image_url, status, metadata, created_at, updated_at
        """,
        params,
    ).fetchone()


def piece_costs_by_id(conn, tenant_organization_id: UUID, piece_ids: list[UUID]) -> dict[UUID, int]:
    if not piece_ids:
        return {}
    rows = conn.execute(
        "select id, unit_cost_cents from kit_pieces where tenant_organization_id = %s and id = any(%s)",
        (tenant_organization_id, piece_ids),
    ).fetchall()
    return {row["id"]: row["unit_cost_cents"] for row in rows}


def create_kit_definition(conn, tenant_organization_id: UUID, payload: dict[str, Any]):
    return conn.execute(
        """
        insert into kit_definitions (tenant_organization_id, name, level, description, status, pieces)
        values (%s, %s, %s, %s, %s, %s)
        returning id, name, level, description, status, pieces, created_at, updated_at
        """,
        (
            tenant_organization_id,
            payload["name"],
            payload["level"],
            payload.get("description"),
            payload.get("status", "active"),
            Jsonb(payload.get("pieces", [])),
        ),
    ).fetchone()


def list_kit_definitions(conn, tenant_organization_id: UUID):
    return conn.execute(
        """
        select id, name, level, description, status, pieces, created_at, updated_at
        from kit_definitions
        where tenant_organization_id = %s
        order by status, name
        """,
        (tenant_organization_id,),
    ).fetchall()


def get_kit_definition(conn, tenant_organization_id: UUID, kit_definition_id: UUID):
    return conn.execute(
        """
        select id, name, level, description, status, pieces, created_at, updated_at
        from kit_definitions
        where id = %s and tenant_organization_id = %s
        """,
        (kit_definition_id, tenant_organization_id),
    ).fetchone()


def update_kit_definition(conn, tenant_organization_id: UUID, kit_definition_id: UUID, updates: dict[str, Any]):
    if not updates:
        return get_kit_definition(conn, tenant_organization_id, kit_definition_id)
    columns = []
    params: list[Any] = []
    for key, value in updates.items():
        columns.append(f"{key} = %s")
        params.append(Jsonb(value) if key == "pieces" else value)
    params.extend([kit_definition_id, tenant_organization_id])
    return conn.execute(
        f"""
        update kit_definitions
        set {", ".join(columns)}, updated_at = now()
        where id = %s and tenant_organization_id = %s
        returning id, name, level, description, status, pieces, created_at, updated_at
        """,
        params,
    ).fetchone()


def create_shipment(conn, kit_definition_id: UUID, client_id: UUID, created_by: UUID, notes: str | None):
    return conn.execute(
        """
        insert into kit_shipments (kit_definition_id, client_id, created_by, notes)
        values (%s, %s, %s, %s)
        returning id
        """,
        (kit_definition_id, client_id, created_by, notes),
    ).fetchone()["id"]


def update_shipment_status(conn, tenant_organization_id: UUID, shipment_id: UUID, status: str, notes: str | None):
    timestamp_column = {"enviado": "shipped_at", "entregue": "delivered_at"}.get(status)
    set_clause = "status = %s, notes = coalesce(%s, notes), updated_at = now()"
    params: list[Any] = [status, notes]
    if timestamp_column:
        set_clause += f", {timestamp_column} = now()"
    return conn.execute(
        f"""
        update kit_shipments s
        set {set_clause}
        from kit_definitions d
        where s.id = %s and s.kit_definition_id = d.id and d.tenant_organization_id = %s
        returning s.id
        """,
        (*params, shipment_id, tenant_organization_id),
    ).fetchone()


def list_shipments(conn, tenant_organization_id: UUID, client_id: UUID | None = None):
    return conn.execute(
        """
        select s.id, s.kit_definition_id, d.name as kit_name, s.client_id, c.name as client_name,
               s.status, s.notes, s.shipped_at, s.delivered_at, s.created_at, s.updated_at
        from kit_shipments s
        join kit_definitions d on d.id = s.kit_definition_id
        join clients c on c.id = s.client_id
        where d.tenant_organization_id = %s
          and (%s::uuid is null or s.client_id = %s)
        order by s.created_at desc
        """,
        (tenant_organization_id, client_id, client_id),
    ).fetchall()


def find_client_organization(conn, client_id: UUID, tenant_organization_id: UUID):
    return conn.execute(
        """
        select c.id
        from clients c
        join organizations o on o.id = c.organization_id
        where c.id = %s and o.parent_organization_id = %s
        """,
        (client_id, tenant_organization_id),
    ).fetchone()
