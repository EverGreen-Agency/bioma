from uuid import UUID
from psycopg.types.json import Jsonb


def get_active_brand_book(conn, workspace_id: UUID):
    row = conn.execute(
        """
        select id, workspace_id, version, tom_de_voz, arquetipo, posicionamento,
               proposta_valor, regras_copy, paleta_cores, status, created_at, updated_at
        from workspace_brand_books
        where workspace_id = %s and status = 'active'
        order by version desc
        limit 1
        """,
        (workspace_id,),
    ).fetchone()
    if not row:
        # Initial default brand book
        return conn.execute(
            """
            insert into workspace_brand_books (workspace_id)
            values (%s)
            returning id, workspace_id, version, tom_de_voz, arquetipo, posicionamento,
                      proposta_valor, regras_copy, paleta_cores, status, created_at, updated_at
            """,
            (workspace_id,),
        ).fetchone()
    return row


def upsert_brand_book(conn, workspace_id: UUID, payload: dict):
    current = get_active_brand_book(conn, workspace_id)
    next_version = (current["version"] + 1) if current else 1

    return conn.execute(
        """
        insert into workspace_brand_books (
          workspace_id, version, tom_de_voz, arquetipo, posicionamento,
          proposta_valor, regras_copy, paleta_cores, status
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, 'active')
        returning id, workspace_id, version, tom_de_voz, arquetipo, posicionamento,
                  proposta_valor, regras_copy, paleta_cores, status, created_at, updated_at
        """,
        (
            workspace_id,
            next_version,
            payload.get("tom_de_voz", "Profissional e Direto"),
            payload.get("arquetipo", "O Governante"),
            payload.get("posicionamento"),
            payload.get("proposta_valor"),
            Jsonb(payload.get("regras_copy", [])),
            Jsonb(payload.get("paleta_cores", [])),
        ),
    ).fetchone()
