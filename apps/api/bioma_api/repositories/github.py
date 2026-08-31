from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb


def find_connection(conn, project_id: UUID):
    return conn.execute(
        "select * from project_github_connections where project_id = %s",
        (project_id,),
    ).fetchone()


def upsert_connection(conn, project_id: UUID, user_id: UUID, payload: dict[str, Any]):
    return conn.execute(
        """
        insert into project_github_connections (
          project_id, repository_owner, repository_name, default_branch, status, created_by, updated_by
        ) values (%s, %s, %s, %s, %s, %s, %s)
        on conflict (project_id) do update set
          repository_owner = excluded.repository_owner,
          repository_name = excluded.repository_name,
          default_branch = excluded.default_branch,
          status = excluded.status,
          updated_by = excluded.updated_by,
          updated_at = now()
        returning *
        """,
        (
            project_id,
            payload["repository_owner"],
            payload["repository_name"],
            payload["default_branch"],
            payload["status"],
            user_id,
            user_id,
        ),
    ).fetchone()


def find_deliverable_for_issue(conn, deliverable_id: UUID):
    return conn.execute(
        """
        select id, title, project_id, github_issue_number, github_issue_url,
          github_issue_write_status, github_issue_write_requested_at
        from deliverables
        where id = %s
        """,
        (deliverable_id,),
    ).fetchone()


def reserve_deliverable_issue(conn, deliverable_id: UUID):
    return conn.execute(
        """
        update deliverables
        set github_issue_write_status = 'pending',
            github_issue_write_error = null,
            github_issue_write_requested_at = now(),
            updated_at = now()
        where id = %s and github_issue_number is null
          and (
            github_issue_write_status in ('idle', 'failed')
            or github_issue_write_requested_at < now() - interval '5 minutes'
          )
        returning id
        """,
        (deliverable_id,),
    ).fetchone()


def record_deliverable_issue(conn, deliverable_id: UUID, issue_number: int, issue_url: str) -> None:
    conn.execute(
        """
        update deliverables
        set github_issue_number = %s, github_issue_url = %s,
            github_issue_write_status = 'completed',
            github_issue_write_error = null,
            updated_at = now()
        where id = %s
        """,
        (issue_number, issue_url, deliverable_id),
    )


def fail_deliverable_issue(conn, deliverable_id: UUID, error_detail: str) -> None:
    conn.execute(
        """
        update deliverables
        set github_issue_write_status = 'failed',
            github_issue_write_error = %s,
            updated_at = now()
        where id = %s and github_issue_number is null
        """,
        (error_detail[:1000], deliverable_id),
    )


def write_audit(conn, actor_user_id: UUID, organization_id: UUID, event_type: str, metadata: dict[str, Any]):
    conn.execute(
        "insert into audit_logs (actor_user_id, organization_id, event_type, metadata) values (%s, %s, %s, %s)",
        (actor_user_id, organization_id, event_type, Jsonb(metadata)),
    )


def find_activity_sync(conn, idempotency_key: str):
    return conn.execute(
        """
        select sync.*, connection.repository_owner, connection.repository_name,
          update.client_visible
        from project_github_activity_syncs sync
        join project_github_connections connection on connection.project_id = sync.project_id
        join project_updates update on update.id = sync.project_update_id
        where sync.idempotency_key = %s
        """,
        (idempotency_key,),
    ).fetchone()


def create_activity_sync(
    conn,
    project_id: UUID,
    idempotency_key: str,
    snapshot: dict[str, Any],
    project_update_id: UUID,
    actor_user_id: UUID,
):
    return conn.execute(
        """
        insert into project_github_activity_syncs (
          project_id, idempotency_key, snapshot, project_update_id, created_by
        ) values (%s, %s, %s, %s, %s)
        returning *
        """,
        (project_id, idempotency_key, Jsonb(snapshot), project_update_id, actor_user_id),
    ).fetchone()


def list_deliverables_with_issues(conn, project_id: UUID) -> list[dict[str, Any]]:
    """Entregas do projeto que já têm issue criada no GitHub.

    Base da conciliação: sem isto não dá para saber quais entregas têm um
    espelho lá fora cujo estado possa ter divergido.
    """
    return conn.execute(
        """
        select id, title, status, completed_at, github_issue_number, github_issue_url
        from deliverables
        where project_id = %s and github_issue_number is not null
        order by github_issue_number
        """,
        (project_id,),
    ).fetchall()
