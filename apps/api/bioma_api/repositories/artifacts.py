from typing import Any
from uuid import UUID

COLUMNS = """
  a.id, a.organization_id, a.workspace_id, a.title, a.kind, a.visibility,
  a.url, a.content, a.status, a.current_version, a.thread_id, a.run_id,
  a.created_by, a.created_at, a.updated_at
"""


def list_for_workspace(
    conn, workspace_id: UUID, kind: str | None = None, status: str | None = None
) -> list[dict[str, Any]]:
    """Vista do Estúdio: os artefatos de um workspace, mais recente primeiro.

    `versions_total` vem junto porque a lista precisa mostrar "v3" sem uma
    segunda consulta por linha — é a diferença entre uma listagem e N+1."""
    return conn.execute(
        f"""
        select {COLUMNS},
          (select count(*) from artifact_versions v where v.artifact_id = a.id)::int as versions_total,
          u.display_name as created_by_name
        from artifacts a
        left join users u on u.id = a.created_by
        where a.workspace_id = %s
          and (%s::text is null or a.kind = %s)
          and (%s::text is null or a.status = %s)
        order by a.updated_at desc, a.created_at desc
        limit 200
        """,
        (workspace_id, kind, kind, status, status),
    ).fetchall()


def find(conn, artifact_id: UUID) -> dict[str, Any] | None:
    return conn.execute(
        f"""
        select {COLUMNS},
          (select count(*) from artifact_versions v where v.artifact_id = a.id)::int as versions_total,
          u.display_name as created_by_name
        from artifacts a
        left join users u on u.id = a.created_by
        where a.id = %s
        """,
        (artifact_id,),
    ).fetchone()


def list_versions(conn, artifact_id: UUID) -> list[dict[str, Any]]:
    return conn.execute(
        """
        select v.id, v.artifact_id, v.version, v.title, v.content, v.url,
               v.run_id, v.change_note, v.created_by, v.created_at,
               u.display_name as created_by_name
        from artifact_versions v
        left join users u on u.id = v.created_by
        where v.artifact_id = %s
        order by v.version desc
        """,
        (artifact_id,),
    ).fetchall()


def create(conn, payload: dict[str, Any], created_by: UUID) -> UUID:
    """Cria o artefato e a v1 na mesma transação.

    As duas coisas juntas de propósito: um artefato sem versão nenhuma seria um
    estado que a tela não sabe desenhar, e é exatamente o que aconteceria se o
    segundo insert falhasse."""
    artifact_id = conn.execute(
        """
        insert into artifacts (
          organization_id, workspace_id, title, kind, visibility, content, url,
          status, thread_id, run_id, created_by
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning id
        """,
        (
            payload["organization_id"],
            payload["workspace_id"],
            payload["title"],
            payload["kind"],
            payload.get("visibility", "internal"),
            payload.get("content"),
            payload.get("url"),
            payload.get("status", "draft"),
            payload.get("thread_id"),
            payload.get("run_id"),
            created_by,
        ),
    ).fetchone()["id"]

    conn.execute(
        """
        insert into artifact_versions (
          artifact_id, version, title, content, url, run_id, change_note, created_by
        )
        values (%s, 1, %s, %s, %s, %s, %s, %s)
        """,
        (
            artifact_id,
            payload["title"],
            payload.get("content"),
            payload.get("url"),
            payload.get("run_id"),
            payload.get("change_note"),
            created_by,
        ),
    )
    return artifact_id


def add_version(conn, artifact_id: UUID, payload: dict[str, Any], created_by: UUID) -> int:
    """Nova versão + atualização da corrente, atomicamente.

    O número sai de `max(version) + 1` lido DENTRO da transação, e não de um
    contador na aplicação: dois pedidos simultâneos gerariam a mesma v2, e o
    `unique (artifact_id, version)` recusaria a segunda em vez de sobrescrever
    calado."""
    next_version = conn.execute(
        "select coalesce(max(version), 0) + 1 as next from artifact_versions where artifact_id = %s",
        (artifact_id,),
    ).fetchone()["next"]

    conn.execute(
        """
        insert into artifact_versions (
          artifact_id, version, title, content, url, run_id, change_note, created_by
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            artifact_id,
            next_version,
            payload["title"],
            payload.get("content"),
            payload.get("url"),
            payload.get("run_id"),
            payload.get("change_note"),
            created_by,
        ),
    )

    # `artifacts.content` é sempre a versão corrente — as telas antigas leem de
    # lá e não deveriam precisar saber que versionamento existe.
    conn.execute(
        """
        update artifacts
        set title = %s, content = %s, url = %s,
            current_version = %s, run_id = coalesce(%s, run_id), updated_at = now()
        where id = %s
        """,
        (
            payload["title"],
            payload.get("content"),
            payload.get("url"),
            next_version,
            payload.get("run_id"),
            artifact_id,
        ),
    )
    return next_version


def set_status(conn, artifact_id: UUID, status: str) -> bool:
    row = conn.execute(
        "update artifacts set status = %s, updated_at = now() where id = %s returning id",
        (status, artifact_id),
    ).fetchone()
    return row is not None


def list_kinds(conn, workspace_id: UUID) -> list[dict[str, Any]]:
    """Os tipos que EXISTEM neste workspace, com contagem.

    O catálogo de tipos é aberto (`kind` é texto livre), então a tela não pode
    partir de uma lista fixa — ela descobre o que há."""
    return conn.execute(
        """
        select kind, count(*)::int as total
        from artifacts
        where workspace_id = %s
        group by kind
        order by total desc, kind asc
        """,
        (workspace_id,),
    ).fetchall()
