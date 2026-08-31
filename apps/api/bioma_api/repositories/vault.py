from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb


SUMMARY_COLUMNS = """
  credential.id, credential.workspace_id, credential.platform, credential.label,
  credential.account_hint, credential.platform_url, credential.visibility, credential.status, credential.expires_at,
  credential.owner_user_id, owner.display_name as owner_name, credential.version,
  credential.last_rotated_at, credential.created_at, credential.updated_at
"""


def find_workspace_context(conn, workspace_id: UUID, is_admin: bool, user_id: UUID):
    return conn.execute(
        """
        select w.id as workspace_id, w.tenant_organization_id, w.subject_organization_id,
          case when %s then 'platform_admin' else workspace_access_role(w.id, %s) end as access_role
        from workspaces w
        where w.id = %s
          and w.status = 'active'
          and (%s or workspace_access_role(w.id, %s) is not null)
        """,
        (is_admin, user_id, workspace_id, is_admin, user_id),
    ).fetchone()


def list_credentials(conn, workspace_id: UUID, include_internal: bool):
    return conn.execute(
        f"""
        select {SUMMARY_COLUMNS}
        from vault_credentials credential
        left join users owner on owner.id = credential.owner_user_id
        where credential.workspace_id = %s
          and (%s or credential.visibility = 'client')
        order by credential.platform, credential.label, credential.updated_at desc
        """,
        (workspace_id, include_internal),
    ).fetchall()


def create_credential(conn, context, user_id: UUID, payload: dict[str, Any]):
    return conn.execute(
        f"""
        with inserted as (
          insert into vault_credentials (
            tenant_organization_id, workspace_id, platform, label, account_hint, platform_url,
            visibility, expires_at, owner_user_id, created_by, updated_by,
            encrypted_username, encrypted_email, encrypted_password, encrypted_other_access, encrypted_token,
            encrypted_recovery_codes, encrypted_notes
          ) values (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s
          ) returning *
        )
        select {SUMMARY_COLUMNS.replace('credential.', 'inserted.')}
        from inserted
        left join users owner on owner.id = inserted.owner_user_id
        """,
        (
            context["tenant_organization_id"],
            context["workspace_id"],
            payload["platform"],
            payload["label"],
            payload.get("account_hint"),
            payload.get("platform_url"),
            payload["visibility"],
            payload.get("expires_at"),
            payload.get("owner_user_id"),
            user_id,
            user_id,
            payload.get("encrypted_username"),
            payload.get("encrypted_email"),
            payload.get("encrypted_password"),
            payload.get("encrypted_other_access"),
            payload.get("encrypted_token"),
            payload.get("encrypted_recovery_codes"),
            payload.get("encrypted_notes"),
        ),
    ).fetchone()


def find_credential(conn, workspace_id: UUID, credential_id: UUID):
    return conn.execute(
        """
        select * from vault_credentials
        where id = %s and workspace_id = %s
        """,
        (credential_id, workspace_id),
    ).fetchone()


def user_belongs_to_workspace(conn, workspace_id: UUID, user_id: UUID) -> bool:
    return bool(
        conn.execute(
            "select workspace_access_role(%s, %s) is not null as allowed",
            (workspace_id, user_id),
        ).fetchone()["allowed"]
    )


def update_credential(conn, workspace_id: UUID, credential_id: UUID, user_id: UUID, payload: dict[str, Any]):
    assignments = []
    values: list[Any] = []
    for column in (
        "platform", "label", "account_hint", "platform_url", "visibility", "expires_at", "owner_user_id",
        "encrypted_username", "encrypted_email", "encrypted_password", "encrypted_other_access", "encrypted_token",
        "encrypted_recovery_codes", "encrypted_notes",
    ):
        if column in payload:
            assignments.append(f"{column} = %s")
            values.append(payload[column])
    if any(column.startswith("encrypted_") for column in payload):
        assignments.extend(("version = version + 1", "last_rotated_at = now()"))
    assignments.extend(("updated_by = %s", "updated_at = now()"))
    values.extend((user_id, credential_id, workspace_id))
    return conn.execute(
        f"""
        update vault_credentials
        set {', '.join(assignments)}
        where id = %s and workspace_id = %s
        returning *
        """,
        tuple(values),
    ).fetchone()


def update_status(conn, workspace_id: UUID, credential_id: UUID, user_id: UUID, new_status: str):
    return conn.execute(
        """
        update vault_credentials
        set status = %s, updated_by = %s, updated_at = now()
        where id = %s and workspace_id = %s
        returning *
        """,
        (new_status, user_id, credential_id, workspace_id),
    ).fetchone()


def write_audit(
    conn,
    actor_user_id: UUID,
    organization_id: UUID,
    event_type: str,
    metadata: dict[str, Any],
) -> None:
    conn.execute(
        """
        insert into audit_logs (actor_user_id, organization_id, event_type, metadata)
        values (%s, %s, %s, %s)
        """,
        (actor_user_id, organization_id, event_type, Jsonb(metadata)),
    )
