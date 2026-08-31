from typing import Any
from uuid import UUID

GRANT_COLUMNS = "id, surface_key, team_id, user_id, effect, note, created_by, created_at, updated_at"


def list_grants_for_user(conn, user_id: UUID) -> list[dict[str, Any]]:
    """Exceções que valem para esta pessoa: as dela e as das equipes dela.

    Uma consulta só (em vez de "buscar equipes" e depois "buscar grants") porque
    as duas metades precisam ser do mesmo instante — trocar de equipe entre as
    duas leituras produziria um menu que não corresponde a permissão nenhuma.
    `team_name` vem junto: é o que a tela mostra em "herdado da equipe X".
    """
    return conn.execute(
        """
        select g.surface_key, g.effect, g.note, g.user_id, g.team_id, t.name as team_name
        from surface_grants g
        left join teams t on t.id = g.team_id
        where g.user_id = %s
           or g.team_id in (
                select tm.team_id
                from team_memberships tm
                join teams t2 on t2.id = tm.team_id and t2.status = 'active'
                where tm.user_id = %s
              )
        order by g.surface_key, lower(coalesce(t.name, ''))
        """,
        (user_id, user_id),
    ).fetchall()


def list_hidden_keys(conn, user_id: UUID) -> list[str]:
    rows = conn.execute(
        "select surface_key from surface_preferences where user_id = %s",
        (user_id,),
    ).fetchall()
    return [row["surface_key"] for row in rows]


def hide(conn, user_id: UUID, surface_key: str) -> None:
    conn.execute(
        """
        insert into surface_preferences (user_id, surface_key)
        values (%s, %s)
        on conflict (user_id, surface_key) do update set updated_at = now()
        """,
        (user_id, surface_key),
    )


def unhide(conn, user_id: UUID, surface_key: str) -> None:
    """Apaga a linha em vez de gravar `false`.

    Voltar a herdar é diferente de fixar "quero ver": se um admin liberar ou
    bloquear a tela depois, a ausência de linha acompanha a mudança e um
    `false` gravado a mascararia.
    """
    conn.execute(
        "delete from surface_preferences where user_id = %s and surface_key = %s",
        (user_id, surface_key),
    )


def list_grants_for_team(conn, team_id: UUID) -> list[dict[str, Any]]:
    return conn.execute(
        f"select {GRANT_COLUMNS} from surface_grants where team_id = %s order by surface_key",
        (team_id,),
    ).fetchall()


def list_grants_for_subject_user(conn, user_id: UUID) -> list[dict[str, Any]]:
    return conn.execute(
        f"select {GRANT_COLUMNS} from surface_grants where user_id = %s order by surface_key",
        (user_id,),
    ).fetchall()


def upsert_team_grant(
    conn, team_id: UUID, surface_key: str, effect: str, note: str | None, created_by: UUID
) -> dict[str, Any]:
    return conn.execute(
        f"""
        insert into surface_grants (surface_key, team_id, effect, note, created_by)
        values (%s, %s, %s, %s, %s)
        on conflict (team_id, surface_key) where team_id is not null
        do update set effect = excluded.effect, note = excluded.note, updated_at = now()
        returning {GRANT_COLUMNS}
        """,
        (surface_key, team_id, effect, note, created_by),
    ).fetchone()


def upsert_user_grant(
    conn, user_id: UUID, surface_key: str, effect: str, note: str | None, created_by: UUID
) -> dict[str, Any]:
    return conn.execute(
        f"""
        insert into surface_grants (surface_key, user_id, effect, note, created_by)
        values (%s, %s, %s, %s, %s)
        on conflict (user_id, surface_key) where user_id is not null
        do update set effect = excluded.effect, note = excluded.note, updated_at = now()
        returning {GRANT_COLUMNS}
        """,
        (surface_key, user_id, effect, note, created_by),
    ).fetchone()


def clear_team_grant(conn, team_id: UUID, surface_key: str) -> bool:
    row = conn.execute(
        "delete from surface_grants where team_id = %s and surface_key = %s returning id",
        (team_id, surface_key),
    ).fetchone()
    return row is not None


def clear_user_grant(conn, user_id: UUID, surface_key: str) -> bool:
    row = conn.execute(
        "delete from surface_grants where user_id = %s and surface_key = %s returning id",
        (user_id, surface_key),
    ).fetchone()
    return row is not None
