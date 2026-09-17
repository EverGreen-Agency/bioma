"""Persistência do rate limit de login (SEC-003).

SQL puro; a política de janela/limite fica em `services/rate_limit.py`.
"""


def count_recent_attempts(conn, key_hash: str, window_seconds: int) -> int:
    row = conn.execute(
        """
        select count(*) as total
        from login_attempts
        where key_hash = %s
          and attempted_at > now() - make_interval(secs => %s)
        """,
        (key_hash, window_seconds),
    ).fetchone()
    return int(row["total"]) if row else 0


def record_attempt(conn, key_hash: str) -> None:
    conn.execute("insert into login_attempts (key_hash) values (%s)", (key_hash,))


def clear_attempts(conn, key_hash: str) -> None:
    conn.execute("delete from login_attempts where key_hash = %s", (key_hash,))


def purge_expired(conn, window_seconds: int) -> int:
    rows = conn.execute(
        """
        delete from login_attempts
        where attempted_at < now() - make_interval(secs => %s)
        returning id
        """,
        (window_seconds,),
    ).fetchall()
    return len(rows)
