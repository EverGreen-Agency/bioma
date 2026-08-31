from uuid import UUID


def list_for_user(conn, user_id: UUID):
    return conn.execute(
        """
        select id, provider, email, created_at
        from identities
        where user_id = %s
        order by created_at
        """,
        (user_id,),
    ).fetchall()


def find_by_subject(conn, provider: str, subject: str):
    return conn.execute(
        """
        select i.id, i.user_id, i.email, u.is_active
        from identities i
        join users u on u.id = i.user_id
        where i.provider = %s and i.provider_subject = %s
        """,
        (provider, subject),
    ).fetchone()


def find_for_user_by_provider(conn, user_id: UUID, provider: str):
    return conn.execute(
        "select id, email from identities where user_id = %s and provider = %s",
        (user_id, provider),
    ).fetchone()


def create(conn, user_id: UUID, provider: str, subject: str, email: str | None) -> UUID:
    return conn.execute(
        """
        insert into identities (user_id, provider, provider_subject, email)
        values (%s, %s, %s, %s)
        returning id
        """,
        (user_id, provider, subject, email),
    ).fetchone()["id"]


def delete(conn, user_id: UUID, identity_id: UUID) -> bool:
    deleted = conn.execute(
        "delete from identities where id = %s and user_id = %s returning id",
        (identity_id, user_id),
    ).fetchone()
    return deleted is not None


def user_has_password(conn, user_id: UUID) -> bool:
    row = conn.execute(
        "select password_hash from users where id = %s",
        (user_id,),
    ).fetchone()
    return bool(row and row["password_hash"])
