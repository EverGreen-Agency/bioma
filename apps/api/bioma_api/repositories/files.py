from uuid import UUID


def list_files(conn, organization_id: UUID, is_admin: bool):
    return conn.execute(
        """
        select id, file_name, content_type, size_bytes, visibility, uploaded_by, created_at
        from client_files
        where organization_id = %s
          and (%s or visibility = 'client')
        order by created_at desc
        limit 100
        """,
        (organization_id, is_admin),
    ).fetchall()


def get_file(conn, organization_id: UUID, file_id: UUID):
    return conn.execute(
        """
        select id, organization_id, file_name, content_type, size_bytes, visibility, storage_key, uploaded_by, created_at
        from client_files
        where id = %s and organization_id = %s
        """,
        (file_id, organization_id),
    ).fetchone()


def create_file(
    conn,
    organization_id: UUID,
    file_name: str,
    content_type: str,
    size_bytes: int,
    visibility: str,
    storage_key: str,
    uploaded_by: UUID,
) -> UUID:
    return conn.execute(
        """
        insert into client_files (
          organization_id, file_name, content_type, size_bytes, visibility, storage_key, uploaded_by
        )
        values (%s, %s, %s, %s, %s, %s, %s)
        returning id
        """,
        (organization_id, file_name, content_type, size_bytes, visibility, storage_key, uploaded_by),
    ).fetchone()["id"]


def delete_file(conn, organization_id: UUID, file_id: UUID) -> bool:
    deleted = conn.execute(
        "delete from client_files where id = %s and organization_id = %s returning id",
        (file_id, organization_id),
    ).fetchone()
    return deleted is not None
