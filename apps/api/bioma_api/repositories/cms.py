"""Alvos de CMS e o registro de onde cada versão foi publicada — decisão 14.

Nenhuma função aqui devolve segredo. O alvo aponta para uma linha do cofre
(`credential_id`) e quem decifra é o serviço, no momento de publicar. Trazer o
segredo junto da listagem faria a senha do WordPress passear por toda tela que
lista alvos.
"""

from typing import Any
from uuid import UUID

TARGET_COLUMNS = """
  t.id, t.tenant_organization_id, t.workspace_id, t.label, t.kind, t.site_url,
  t.credential_id, t.publish_mode, t.is_active, t.last_checked_at,
  t.last_check_error, t.created_at, t.updated_at
"""


def list_targets(conn, workspace_id: UUID) -> list[dict[str, Any]]:
    return conn.execute(
        f"""
        select {TARGET_COLUMNS}, c.label as credential_label
        from cms_targets t
        join vault_credentials c on c.id = t.credential_id
        where t.workspace_id = %s
        order by t.is_active desc, t.label asc
        """,
        (workspace_id,),
    ).fetchall()


def find_target(conn, target_id: UUID) -> dict[str, Any] | None:
    return conn.execute(
        f"""
        select {TARGET_COLUMNS}, c.label as credential_label
        from cms_targets t
        join vault_credentials c on c.id = t.credential_id
        where t.id = %s
        """,
        (target_id,),
    ).fetchone()


def credential_in_workspace(conn, workspace_id: UUID, credential_id: UUID) -> bool:
    """A credencial tem que ser DO MESMO workspace do alvo.

    Sem esta checagem, apontar um alvo para uma credencial de outro cliente
    seria um caminho de leitura cruzada — e a API decifraria de bom grado.
    """
    row = conn.execute(
        "select 1 from vault_credentials where id = %s and workspace_id = %s",
        (credential_id, workspace_id),
    ).fetchone()
    return row is not None


def create_target(conn, workspace_id: UUID, tenant_organization_id: UUID, payload: dict[str, Any], created_by: UUID) -> UUID:
    return conn.execute(
        """
        insert into cms_targets (
          tenant_organization_id, workspace_id, label, kind, site_url,
          credential_id, publish_mode, created_by
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (workspace_id, site_url) do update set
          label = excluded.label,
          credential_id = excluded.credential_id,
          publish_mode = excluded.publish_mode,
          is_active = true,
          updated_at = now()
        returning id
        """,
        (
            tenant_organization_id,
            workspace_id,
            payload["label"],
            payload.get("kind", "wordpress"),
            payload["site_url"],
            payload["credential_id"],
            payload.get("publish_mode", "draft"),
            created_by,
        ),
    ).fetchone()["id"]


def update_target(conn, target_id: UUID, updates: dict[str, Any]) -> bool:
    if not updates:
        return True
    set_clause = ", ".join(f"{coluna} = %s" for coluna in updates)
    params = [*updates.values(), target_id]
    row = conn.execute(
        f"update cms_targets set {set_clause}, updated_at = now() where id = %s returning id",
        params,
    ).fetchone()
    return row is not None


def record_check(conn, target_id: UUID, erro: str | None) -> None:
    """Guarda o resultado do teste de conexão — inclusive quando falhou.

    Guardar só o sucesso deixaria a tela dizendo "verificado em 12/08" para um
    alvo que parou de funcionar em 13/08.
    """
    conn.execute(
        """
        update cms_targets
        set last_checked_at = now(), last_check_error = %s, updated_at = now()
        where id = %s
        """,
        (erro, target_id),
    )


def record_publication(
    conn,
    artifact_id: UUID,
    version: int,
    target_id: UUID,
    resultado: dict[str, Any],
    published_by: UUID,
) -> dict[str, Any]:
    return conn.execute(
        """
        insert into artifact_publications (
          artifact_id, version, target_id, external_id, external_url,
          external_status, published_by
        )
        values (%s, %s, %s, %s, %s, %s, %s)
        on conflict (artifact_id, target_id) do update set
          version = excluded.version,
          external_id = excluded.external_id,
          external_url = excluded.external_url,
          external_status = excluded.external_status,
          published_by = excluded.published_by,
          published_at = now()
        returning id, artifact_id, version, target_id, external_id,
                  external_url, external_status, published_at
        """,
        (
            artifact_id,
            version,
            target_id,
            str(resultado["id"]),
            resultado.get("link"),
            resultado.get("status"),
            published_by,
        ),
    ).fetchone()


def find_publication(conn, artifact_id: UUID, target_id: UUID) -> dict[str, Any] | None:
    """A publicacao deste artigo NESTE alvo, se existir.

    E o que decide entre criar e atualizar no CMS. Sem esta consulta, publicar
    de novo criava post duplicado no site do cliente.
    """
    return conn.execute(
        """
        select id, artifact_id, version, target_id, external_id, external_url,
               external_status, published_at
        from artifact_publications
        where artifact_id = %s and target_id = %s
        """,
        (artifact_id, target_id),
    ).fetchone()


def list_publications(conn, artifact_id: UUID) -> list[dict[str, Any]]:
    return conn.execute(
        """
        select p.id, p.artifact_id, p.version, p.target_id, p.external_id,
               p.external_url, p.external_status, p.published_at,
               t.label as target_label, t.site_url
        from artifact_publications p
        join cms_targets t on t.id = p.target_id
        where p.artifact_id = %s
        order by p.published_at desc
        """,
        (artifact_id,),
    ).fetchall()


def list_publications_for_target(conn, target_id: UUID) -> list[dict[str, Any]]:
    """O que o Bioma publicou NESTE alvo.

    Serve para cruzar com a listagem vinda do site e dizer quais posts têm
    artefato por trás. Post escrito direto no WordPress fica sem vínculo, e isso
    é informação sobre a origem — não um buraco.
    """
    return conn.execute(
        """
        select artifact_id, version, external_id
        from artifact_publications
        where target_id = %s
        """,
        (target_id,),
    ).fetchall()


def sync_publication_status(conn, target_id: UUID, external_id: str, novo_status: str | None) -> None:
    """Espelha no Bioma o status que o post tem AGORA no CMS.

    Sem isso, tirar um post do ar pela tela do Bioma deixaria o registro daqui
    dizendo "publicado" para sempre — a divergência silenciosa entre as duas
    pontas que a integração existe para evitar.
    """
    if not novo_status:
        return
    conn.execute(
        """
        update artifact_publications
        set external_status = %s
        where target_id = %s and external_id = %s
        """,
        (novo_status, target_id, external_id),
    )
