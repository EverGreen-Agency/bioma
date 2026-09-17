from datetime import datetime
from uuid import UUID


def find_user_by_email(conn, email: str):
    return conn.execute(
        """
        select id, email, display_name, password_hash
        from users
        where lower(email) = %s and is_active = true
        """,
        (email.lower(),),
    ).fetchone()


def get_user(conn, user_id: UUID):
    return conn.execute(
        "select id, email, display_name, password_hash from users where id = %s and is_active = true",
        (user_id,),
    ).fetchone()


def create_reset(conn, user_id: UUID, token_hash: str, expires_at: datetime, created_by: UUID) -> UUID:
    return conn.execute(
        """
        insert into password_resets (user_id, token_hash, expires_at, created_by)
        values (%s, %s, %s, %s)
        returning id
        """,
        (user_id, token_hash, expires_at, created_by),
    ).fetchone()["id"]


def find_valid_reset(conn, token_hash: str):
    return conn.execute(
        """
        select r.id, r.user_id, r.expires_at, u.email, u.display_name
        from password_resets r
        join users u on u.id = r.user_id and u.is_active = true
        where r.token_hash = %s
          and r.used_at is null
          and r.expires_at > now()
        """,
        (token_hash,),
    ).fetchone()


def mark_reset_used(conn, reset_id: UUID) -> None:
    conn.execute("update password_resets set used_at = now() where id = %s", (reset_id,))


def set_password(conn, user_id: UUID, password_hash: str) -> None:
    conn.execute(
        "update users set password_hash = %s, updated_at = now() where id = %s",
        (password_hash, user_id),
    )


def revoke_sessions(conn, user_id: UUID, except_token_hash: str | None = None) -> int:
    if except_token_hash:
        rows = conn.execute(
            """
            update sessions set revoked_at = now()
            where user_id = %s and revoked_at is null and token_hash <> %s
            returning id
            """,
            (user_id, except_token_hash),
        ).fetchall()
    else:
        rows = conn.execute(
            "update sessions set revoked_at = now() where user_id = %s and revoked_at is null returning id",
            (user_id,),
        ).fetchall()
    return len(rows)


def create_session(conn, user_id: UUID, token_hash: str, expires_at: datetime) -> None:
    conn.execute(
        "insert into sessions (user_id, token_hash, expires_at) values (%s, %s, %s)",
        (user_id, token_hash, expires_at),
    )


def user_organizations(conn, user_id: UUID) -> list:
    return [row["organization_id"] for row in conn.execute(
        "select organization_id from memberships where user_id = %s",
        (user_id,),
    ).fetchall()]
