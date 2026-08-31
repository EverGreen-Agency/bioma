from typing import Any
from uuid import UUID


_SELECT = """
    select
      c.id, c.user_id,
      coalesce(u.display_name, 'EverGreen (agência)') as holder_name,
      c.provider, c.name, c.credential_id, c.verification_url,
      c.issued_at, c.expires_at,
      case
        when c.expires_at is null then 'active'
        when c.expires_at < current_date then 'expired'
        when c.expires_at <= current_date + interval '30 days' then 'expiring_soon'
        else 'active'
      end as status,
      c.notes, c.created_at, c.updated_at
    from certifications c
    left join users u on u.id = c.user_id
"""


def create_certification(conn, tenant_organization_id: UUID, created_by: UUID, payload: dict[str, Any]):
    row = conn.execute(
        """
        insert into certifications (tenant_organization_id, user_id, provider, name, credential_id, verification_url, issued_at, expires_at, notes, created_by)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning id
        """,
        (
            tenant_organization_id,
            payload.get("user_id"),
            payload["provider"],
            payload["name"],
            payload.get("credential_id"),
            payload.get("verification_url"),
            payload["issued_at"],
            payload.get("expires_at"),
            payload.get("notes"),
            created_by,
        ),
    ).fetchone()
    return get_certification(conn, tenant_organization_id, row["id"])


def get_certification(conn, tenant_organization_id: UUID, certification_id: UUID):
    return conn.execute(
        f"{_SELECT} where c.id = %s and c.tenant_organization_id = %s",
        (certification_id, tenant_organization_id),
    ).fetchone()


def list_certifications(conn, tenant_organization_id: UUID, user_id: UUID | None = None):
    if user_id is not None:
        return conn.execute(
            f"{_SELECT} where c.tenant_organization_id = %s and c.user_id = %s order by c.expires_at nulls last, c.name",
            (tenant_organization_id, user_id),
        ).fetchall()
    return conn.execute(
        f"{_SELECT} where c.tenant_organization_id = %s order by c.expires_at nulls last, c.name",
        (tenant_organization_id,),
    ).fetchall()


def update_certification(conn, tenant_organization_id: UUID, certification_id: UUID, updates: dict[str, Any]):
    if not updates:
        return get_certification(conn, tenant_organization_id, certification_id)
    columns = [f"{key} = %s" for key in updates]
    params = list(updates.values()) + [certification_id, tenant_organization_id]
    updated = conn.execute(
        f"""
        update certifications
        set {", ".join(columns)}, updated_at = now()
        where id = %s and tenant_organization_id = %s
        returning id
        """,
        params,
    ).fetchone()
    if not updated:
        return None
    return get_certification(conn, tenant_organization_id, certification_id)


def delete_certification(conn, tenant_organization_id: UUID, certification_id: UUID) -> bool:
    deleted = conn.execute(
        "delete from certifications where id = %s and tenant_organization_id = %s returning id",
        (certification_id, tenant_organization_id),
    ).fetchone()
    return bool(deleted)
