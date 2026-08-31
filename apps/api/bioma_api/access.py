"""Regras de acesso compartilhadas: papel de plataforma e feature-gating por organização.

Decisão 2026-07-14 (ROADMAP-MVP.md): módulos habilitados por organização,
EG admin enxerga tudo; `client_user` só o que estiver em `enabled_modules`.
"""

from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.domain.models import Role
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse

CLIENT_MODULES = ("hub", "content", "files", "commercial", "finance", "analytics", "integrations", "engineering")
DEFAULT_CLIENT_MODULES = ("hub", "content", "files")

WORKSPACE_CAPABILITIES = {
    "platform_admin": {"view", "manage_work", "approve", "manage_config", "generate_content", "submit_secrets", "manage_secrets", "reveal_secrets"},
    "tenant_admin": {"view", "manage_work", "approve", "manage_config", "generate_content", "submit_secrets", "manage_secrets", "reveal_secrets"},
    "workspace_manager": {"view", "manage_work", "approve", "manage_config", "generate_content", "submit_secrets", "manage_secrets", "reveal_secrets"},
    "operator": {"view", "manage_work", "generate_content", "submit_secrets", "manage_secrets"},
    "approver": {"view", "approve"},
    "viewer": {"view"},
    "client_user": {"view", "approve", "generate_content", "submit_secrets"},
}

MODULE_LABELS = {
    "hub": "Hub do cliente",
    "content": "Conteúdo",
    "files": "Arquivos",
    "commercial": "Comercial",
    "finance": "Financeiro",
    "analytics": "Analytics",
    "integrations": "Integrações",
    "engineering": "Engenharia",
}


def is_platform_admin(user: CurrentUserResponse) -> bool:
    """Pode ADMINISTRAR a EG: convidar, conceder acesso, mexer em integração.

    Continua exigindo `eg_admin` — `eg_member` (0090) pertence à EG mas não a
    administra. Os dois predicados existem separados porque antes eram a mesma
    pergunta, e é por isso que todo convite ao time criava um administrador.
    """
    return any(org.slug == "eg" and org.role == Role.eg_admin for org in user.organizations)


def is_platform_member(user: CurrentUserResponse) -> bool:
    """Pertence à EG — decide o que a pessoa ENXERGA, não o que ela muda.

    Admin também é membro. Usar isto para visibilidade e `is_platform_admin`
    para escrita é o que permite alguém da equipe existir sem poder de admin.
    """
    return any(
        org.slug == "eg" and org.role in (Role.eg_admin, Role.eg_member)
        for org in user.organizations
    )


def require_platform_admin(user: CurrentUserResponse) -> None:
    if not is_platform_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas EG admin pode executar esta ação.")


def check_organization_access(
    user: CurrentUserResponse,
    organization_id: "UUID | str",
    required_roles: list[str] | None = None,
) -> None:
    """Garante que o usuário pertence à organização (ou é EG admin).

    Criada porque o trabalho do Kommo a referenciava sem implementação —
    a API não subia. Aceita str para validar UUIDs vindos de path params
    tipados como texto (422 em vez de 500 do Postgres).
    """
    try:
        organization_uuid = organization_id if isinstance(organization_id, UUID) else UUID(str(organization_id))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Organização inválida.")

    if is_platform_admin(user):
        return

    roles = set(required_roles or ("eg_admin", "client_user"))
    for organization in user.organizations:
        if organization.id == organization_uuid and organization.role.value in roles:
            return

    # 404 (não 403) para não confirmar a existência da organização a quem não pertence a ela.
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organização não encontrada.")


def require_client_module(client_row, user: CurrentUserResponse, module: str) -> None:
    """Bloqueia `client_user` fora dos módulos habilitados da organização do cliente.

    `client_row` precisa vir de um `find_accessible_client` que selecione
    `enabled_modules` (join com organizations).
    """
    if is_platform_admin(user):
        return
    modules = client_row.get("enabled_modules") or []
    if module not in modules:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Módulo '{MODULE_LABELS.get(module, module)}' não habilitado para este cliente.",
        )


def require_workspace_capability(client_row, user: CurrentUserResponse, capability: str) -> None:
    """Aplica a matriz de autorização ao contexto já resolvido do workspace."""
    role = "platform_admin" if is_platform_admin(user) else client_row.get("access_role")
    if capability in WORKSPACE_CAPABILITIES.get(role, set()):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Seu papel neste workspace não permite esta ação.",
    )


def resolve_accessible_client(
    conn,
    client_id: UUID,
    user: CurrentUserResponse,
    module: str | None = None,
    capability: str | None = None,
    require_kind: str | None = None,
):
    """Ponto único de resolução de cliente/workspace (BOLA/IDOR + gates).

    Antes desta função cada service tinha a sua cópia de `_accessible_client`
    (`client_hub`, `files`, `performance`, `invites`), o que obrigava a
    replicar qualquer mudança de regra em quatro lugares. Os parâmetros
    cobrem as variações que existiam: `module` fixo (`files`/`analytics`),
    `capability` da matriz de papéis e `require_kind` para recusar workspace
    interno onde só cliente faz sentido (convites).

    404 em vez de 403 é intencional: não confirma a existência do cliente a
    quem não tem acesso a ele.
    """
    client = workspaces_repo.find_accessible_client(conn, client_id, is_platform_admin(user), user.id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
    if require_kind and client["workspace_kind"] != require_kind:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
    if module:
        require_client_module(client, user, module)
    if capability:
        require_workspace_capability(client, user, capability)
    return client
