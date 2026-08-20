"""Publicar peça do Estúdio em CMS — decisão 14.

Une três coisas que já existiam separadas: o artefato versionado (decisão 8), a
credencial cifrada no cofre, e o cliente REST do WordPress. Nada de novo é
guardado em segredo — o alvo aponta para a linha do cofre e a decifragem
acontece aqui, no instante de publicar.

**A permissão é atrelada ao risco, não ao botão** (`capability_for_status`):
mandar rascunho exige `manage_work`, colocar no ar exige `approve`. Amarrar ao
botão trataria os dois igual e obrigaria a escolher entre travar o rascunho ou
liberar a publicação.
"""

from uuid import UUID

from fastapi import HTTPException, status

from bioma_api import cms as cms_rules
from bioma_api.access import require_workspace_capability, resolve_accessible_client
from bioma_api.crypto import decrypt_secret, require_encryption_configured
from bioma_api.db import connect
from bioma_api.integrations.wordpress import WordPressClient, WordPressError
from bioma_api.repositories import artifacts as artifacts_repo
from bioma_api.repositories import cms as repo
from bioma_api.repositories import vault as vault_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.cms import (
    ArtifactPublication,
    CmsTarget,
    CmsTargetCheck,
    CmsTargetCreate,
    CmsTargetUpdate,
    PublicationPreview,
    PublishRequest,
)


def list_targets(workspace_id: UUID, user: CurrentUserResponse) -> list[CmsTarget]:
    with connect() as conn:
        context = resolve_accessible_client(conn, workspace_id, user)
        rows = repo.list_targets(conn, context["workspace_id"])
    return [CmsTarget(**row) for row in rows]


def create_target(workspace_id: UUID, payload: CmsTargetCreate, user: CurrentUserResponse) -> CmsTarget:
    with connect() as conn:
        context = resolve_accessible_client(conn, workspace_id, user, capability="manage_config")
        # A credencial tem que ser DO MESMO workspace. Sem isto, apontar um alvo
        # para a credencial de outro cliente seria leitura cruzada — e a API
        # decifraria de bom grado na hora de publicar.
        if not repo.credential_in_workspace(conn, context["workspace_id"], payload.credential_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A credencial escolhida não pertence a este workspace.",
            )
        target_id = repo.create_target(
            conn,
            context["workspace_id"],
            context["tenant_organization_id"],
            payload.model_dump(),
            user.id,
        )
        row = repo.find_target(conn, target_id)
    return CmsTarget(**row)


def update_target(
    workspace_id: UUID, target_id: UUID, payload: CmsTargetUpdate, user: CurrentUserResponse
) -> CmsTarget:
    updates = payload.model_dump(exclude_none=True)
    with connect() as conn:
        context = resolve_accessible_client(conn, workspace_id, user, capability="manage_config")
        _target_do_workspace(conn, context, target_id)
        if "credential_id" in updates and not repo.credential_in_workspace(
            conn, context["workspace_id"], updates["credential_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A credencial escolhida não pertence a este workspace.",
            )
        repo.update_target(conn, target_id, updates)
        row = repo.find_target(conn, target_id)
    return CmsTarget(**row)


def check_target(workspace_id: UUID, target_id: UUID, user: CurrentUserResponse) -> CmsTargetCheck:
    """Testa a credencial contra o site — sem escrever nada lá.

    O resultado é gravado inclusive quando falha: guardar só o sucesso deixaria
    a tela dizendo "verificado em 12/08" para um alvo que parou de funcionar
    no dia 13.
    """
    require_encryption_configured()
    with connect() as conn:
        context = resolve_accessible_client(conn, workspace_id, user, capability="manage_config")
        target = _target_do_workspace(conn, context, target_id)
        usuario, senha = _credencial(conn, target)
        try:
            cliente = WordPressClient(target["site_url"], usuario, senha)
            try:
                cliente.verify()
            finally:
                cliente.close()
        except WordPressError as erro:
            repo.record_check(conn, target_id, str(erro))
            return CmsTargetCheck(ok=False, detail=str(erro))
        repo.record_check(conn, target_id, None)
    return CmsTargetCheck(ok=True, detail="Credencial válida e com permissão para publicar.")


def preview_publication(
    workspace_id: UUID, artifact_id: UUID, payload: PublishRequest, user: CurrentUserResponse
) -> PublicationPreview:
    """Exatamente o que seria enviado — sem enviar.

    O destino é o site do CLIENTE. Ver antes não é conforto: é o que separa um
    erro corrigível de um post publicado em nome dele.
    """
    with connect() as conn:
        context = resolve_accessible_client(conn, workspace_id, user)
        target = _target_do_workspace(conn, context, payload.target_id)
        artefato, versao = _versao(conn, artifact_id, context, payload.version)
        return _montar_preview(target, artefato, versao, payload)


def publish(
    workspace_id: UUID, artifact_id: UUID, payload: PublishRequest, user: CurrentUserResponse
) -> ArtifactPublication:
    require_encryption_configured()
    with connect() as conn:
        context = resolve_accessible_client(conn, workspace_id, user)
        target = _target_do_workspace(conn, context, payload.target_id)
        if not target["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Este alvo está desativado. Reative antes de publicar.",
            )

        artefato, versao = _versao(conn, artifact_id, context, payload.version)
        preview = _montar_preview(target, artefato, versao, payload)

        # A permissão sai do RESULTADO, não do botão. Um operador rascunha à
        # vontade; ir ao ar exige quem aprova.
        require_workspace_capability(
            context, user, cms_rules.capability_for_status(preview.resulting_status)
        )

        usuario, senha = _credencial(conn, target)
        cliente = WordPressClient(target["site_url"], usuario, senha)
        try:
            resultado = cliente.create_post(preview.payload)
        except WordPressError as erro:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(erro)) from None
        finally:
            cliente.close()

        # Auditoria porque um segredo do cofre foi usado. Publicar não revela a
        # credencial para ninguém, mas usa — e o cofre registra uso, não só
        # revelação.
        vault_repo.write_audit(
            conn,
            user.id,
            context["subject_organization_id"],
            "cms.published",
            {
                "workspace_id": str(context["workspace_id"]),
                "credential_id": str(target["credential_id"]),
                "target_id": str(target["id"]),
                "artifact_id": str(artifact_id),
                "version": versao["version"],
                "resulting_status": preview.resulting_status,
                "external_id": str(resultado["id"]),
            },
        )
        linha = repo.record_publication(
            conn, artifact_id, versao["version"], target["id"], resultado, user.id
        )
        linha = {**linha, "target_label": target["label"], "site_url": target["site_url"]}
    return ArtifactPublication(**linha)


def list_publications(workspace_id: UUID, artifact_id: UUID, user: CurrentUserResponse) -> list[ArtifactPublication]:
    with connect() as conn:
        context = resolve_accessible_client(conn, workspace_id, user)
        _artefato_do_workspace(conn, artifact_id, context)
        rows = repo.list_publications(conn, artifact_id)
    return [ArtifactPublication(**row) for row in rows]


# ---------------------------------------------------------------------- interno


def _montar_preview(target, artefato, versao, payload: PublishRequest) -> PublicationPreview:
    resulting_status, motivo = cms_rules.explain_publish_status(
        artifact_status=artefato["status"], mode=target["publish_mode"]
    )
    try:
        corpo = cms_rules.build_post_payload(
            {
                "title": versao["title"],
                "content": versao["content"],
                "status": artefato["status"],
            },
            mode=target["publish_mode"],
            slug=payload.slug,
            categories=payload.categories,
            tags=payload.tags,
        )
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(erro)) from None

    return PublicationPreview(
        target_id=target["id"],
        artifact_id=artefato["id"],
        version=versao["version"],
        resulting_status=resulting_status,
        downgrade_reason=motivo,
        payload=corpo,
    )


def _target_do_workspace(conn, context, target_id: UUID):
    target = repo.find_target(conn, target_id)
    # 404 e não 403: não se confirma a existência do que não é seu.
    if not target or target["workspace_id"] != context["workspace_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alvo de CMS não encontrado.")
    return target


def _artefato_do_workspace(conn, artifact_id: UUID, context):
    artefato = artifacts_repo.find(conn, artifact_id)
    if not artefato or artefato["workspace_id"] != context["workspace_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artefato não encontrado.")
    return artefato


def _versao(conn, artifact_id: UUID, context, version: int | None):
    """A versão pedida, ou a corrente.

    Republicar uma versão antiga é o caso de "voltar para a v2" — sem isso a
    única saída seria criar uma v4 copiando a v2, que polui o histórico com uma
    mudança que não houve.
    """
    artefato = _artefato_do_workspace(conn, artifact_id, context)
    alvo = version or artefato["current_version"]
    versoes = artifacts_repo.list_versions(conn, artifact_id)
    encontrada = next((v for v in versoes if v["version"] == alvo), None)
    if not encontrada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"A peça não tem versão {alvo}.",
        )
    return artefato, encontrada


def _credencial(conn, target) -> tuple[str, str]:
    linha = vault_repo.find_credential(conn, target["workspace_id"], target["credential_id"])
    if not linha:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A credencial deste alvo foi removida do cofre.",
        )
    if linha["status"] in {"compromised", "revoked"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"A credencial está marcada como '{linha['status']}' no cofre e "
                "não pode ser usada. Cadastre outra Application Password."
            ),
        )
    usuario = decrypt_secret(linha.get("encrypted_username"))
    senha = decrypt_secret(linha.get("encrypted_password"))
    if not usuario or not senha:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "A credencial precisa ter usuário e senha preenchidos. A senha é "
                "a Application Password gerada no WordPress."
            ),
        )
    return usuario, senha
