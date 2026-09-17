"""SQL do Wiki EG. Sempre parametrizado; escopo por tenant da agência."""

from uuid import UUID


def list_documents(conn, tenant_id: UUID) -> list[dict]:
    return conn.execute(
        """
        select d.id, d.category, d.title, d.updated_at,
               count(a.id) as attachment_count
        from wiki_documents d
        left join wiki_attachments a on a.document_id = d.id
        where d.tenant_organization_id = %s
        group by d.id
        order by d.category, d.updated_at desc
        """,
        (tenant_id,),
    ).fetchall()


def get_document(conn, tenant_id: UUID, document_id: UUID) -> dict | None:
    return conn.execute(
        """
        select id, category, title, content, updated_at
        from wiki_documents
        where id = %s and tenant_organization_id = %s
        """,
        (document_id, tenant_id),
    ).fetchone()


def list_attachments(conn, document_id: UUID) -> list[dict]:
    return conn.execute(
        """
        select id, file_name, content_type, size_bytes, created_at
        from wiki_attachments
        where document_id = %s
        order by created_at desc
        """,
        (document_id,),
    ).fetchall()


def create_document(conn, tenant_id: UUID, user_id: UUID, category: str, title: str, content: str) -> UUID:
    return conn.execute(
        """
        insert into wiki_documents (tenant_organization_id, category, title, content, created_by)
        values (%s, %s, %s, %s, %s)
        returning id
        """,
        (tenant_id, category, title, content, user_id),
    ).fetchone()["id"]


def update_document(conn, tenant_id: UUID, document_id: UUID, fields: dict) -> bool:
    # Monta o SET apenas com as chaves presentes; nomes de coluna vêm de um
    # allowlist fixo (nunca do request), então a interpolação é segura.
    columns = [key for key in ("category", "title", "content") if key in fields]
    if not columns:
        return get_document(conn, tenant_id, document_id) is not None
    assignments = ", ".join(f"{column} = %s" for column in columns)
    values = [fields[column] for column in columns]
    row = conn.execute(
        f"""
        update wiki_documents
        set {assignments}, updated_at = now()
        where id = %s and tenant_organization_id = %s
        returning id
        """,
        (*values, document_id, tenant_id),
    ).fetchone()
    return row is not None


def delete_document(conn, tenant_id: UUID, document_id: UUID) -> list[str]:
    # Devolve as storage_keys dos anexos para limpeza no S3 antes do cascade.
    keys = [
        row["storage_key"]
        for row in conn.execute(
            """
            select a.storage_key
            from wiki_attachments a
            join wiki_documents d on d.id = a.document_id
            where a.document_id = %s and d.tenant_organization_id = %s
            """,
            (document_id, tenant_id),
        ).fetchall()
    ]
    conn.execute(
        "delete from wiki_documents where id = %s and tenant_organization_id = %s",
        (document_id, tenant_id),
    )
    return keys


def add_attachment(
    conn, document_id: UUID, user_id: UUID, file_name: str, storage_key: str, content_type: str, size_bytes: int
) -> dict:
    return conn.execute(
        """
        insert into wiki_attachments (document_id, file_name, storage_key, content_type, size_bytes, uploaded_by)
        values (%s, %s, %s, %s, %s, %s)
        returning id, file_name, content_type, size_bytes, created_at
        """,
        (document_id, file_name, storage_key, content_type, size_bytes, user_id),
    ).fetchone()


def get_attachment(conn, tenant_id: UUID, attachment_id: UUID) -> dict | None:
    return conn.execute(
        """
        select a.id, a.file_name, a.storage_key
        from wiki_attachments a
        join wiki_documents d on d.id = a.document_id
        where a.id = %s and d.tenant_organization_id = %s
        """,
        (attachment_id, tenant_id),
    ).fetchone()


def delete_attachment(conn, tenant_id: UUID, attachment_id: UUID) -> str | None:
    row = conn.execute(
        """
        delete from wiki_attachments a
        using wiki_documents d
        where a.document_id = d.id
          and a.id = %s and d.tenant_organization_id = %s
        returning a.storage_key
        """,
        (attachment_id, tenant_id),
    ).fetchone()
    return row["storage_key"] if row else None


def document_exists(conn, tenant_id: UUID, document_id: UUID) -> bool:
    return get_document(conn, tenant_id, document_id) is not None


def title_exists(conn, tenant_id: UUID, title: str) -> bool:
    row = conn.execute(
        "select 1 from wiki_documents where tenant_organization_id = %s and lower(title) = lower(%s) limit 1",
        (tenant_id, title),
    ).fetchone()
    return row is not None
