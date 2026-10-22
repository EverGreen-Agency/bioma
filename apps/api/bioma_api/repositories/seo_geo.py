from typing import Any
from uuid import UUID
from psycopg.types.json import Jsonb

AUDIT_COLUMNS = (
    "id, workspace_id, tenant_organization_id, target_url, page_title, "
    "seo_score, geo_score, technical_audit, geo_audit, generated_llms_txt, "
    "generated_schema_jsonld, waf_detected, created_by, created_at, updated_at"
)


def list_audits(conn, workspace_id: UUID, limit: int = 50) -> list[dict[str, Any]]:
    return conn.execute(
        f"""
        SELECT {AUDIT_COLUMNS}
        FROM workspace_seo_geo_audits
        WHERE workspace_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (workspace_id, limit),
    ).fetchall()


def get_audit(conn, workspace_id: UUID, audit_id: UUID) -> dict[str, Any] | None:
    return conn.execute(
        f"""
        SELECT {AUDIT_COLUMNS}
        FROM workspace_seo_geo_audits
        WHERE workspace_id = %s AND id = %s
        """,
        (workspace_id, audit_id),
    ).fetchone()


def insert_audit(
    conn,
    workspace_id: UUID,
    tenant_id: UUID,
    created_by: UUID | None,
    data: dict[str, Any],
) -> dict[str, Any]:
    return conn.execute(
        f"""
        INSERT INTO workspace_seo_geo_audits (
            workspace_id, tenant_organization_id, target_url, page_title,
            seo_score, geo_score, technical_audit, geo_audit,
            generated_llms_txt, generated_schema_jsonld, waf_detected, created_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING {AUDIT_COLUMNS}
        """,
        (
            workspace_id,
            tenant_id,
            data["target_url"],
            data.get("page_title"),
            data["seo_score"],
            data["geo_score"],
            Jsonb(data["technical_audit"]),
            Jsonb(data["geo_audit"]),
            data.get("generated_llms_txt"),
            Jsonb(data.get("generated_schema_jsonld") or {}),
            data.get("waf_detected", False),
            created_by,
        ),
    ).fetchone()


def delete_audit(conn, workspace_id: UUID, audit_id: UUID) -> bool:
    res = conn.execute(
        """
        DELETE FROM workspace_seo_geo_audits
        WHERE workspace_id = %s AND id = %s
        RETURNING id
        """,
        (workspace_id, audit_id),
    ).fetchone()
    return res is not None
