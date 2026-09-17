import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import require_platform_admin, resolve_accessible_client
from bioma_api.config import get_settings
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import invites as invites_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.invites import (
    InviteAcceptRequest,
    InviteCreatedResponse,
    InviteCreateRequest,
    InvitePublicResponse,
    InviteSummary,
    TeamInviteCreateRequest,
)
from bioma_api.security import hash_password, hash_session_token, new_session_token


def create_invite(
    client_id: UUID,
    payload: InviteCreateRequest,
    user: CurrentUserResponse,
) -> InviteCreatedResponse:
    require_platform_admin(user)
    expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)
    token = secrets.token_urlsafe(32)

    with connect() as conn:
        client = _accessible_client(conn, client_id, user)
        invite_id = invites_repo.create_invite(
            conn,
            client["organization_id"],
            payload.email,
            hash_session_token(token),
            expires_at,
            user.id,
        )
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "invite.created",
            {"client_id": str(client_id), "invite_id": str(invite_id), "email": payload.email},
        )

    return InviteCreatedResponse(
        id=invite_id,
        token=token,
        path=f"/convite/{token}",
        email=payload.email,
        expires_at=expires_at,
    )


def create_team_invite(
    tenant_organization_id: UUID,
    payload: TeamInviteCreateRequest,
    user: CurrentUserResponse,
) -> InviteCreatedResponse:
    """Convite para o time da EG, opcionalmente já dentro de uma equipe.

    Diferente do convite de cliente em dois pontos: entra na organização da EG
    (`eg_member` por padrão, `eg_admin` só se escolhido) e pode carregar equipe
    e papel de tenant, para a pessoa não chegar sem lugar nenhum.

    O default ser `eg_member` (0090) é deliberado: até então não havia
    alternativa e todo convite criava administrador. Promover alguém tem que
    ser um ato explícito, não o caminho de menor resistência.

    Reusa o mesmo fluxo público de aceite — token com hash, expiração, uso
    único, criação de conta e sessão. O que muda é só o que o aceite concede.
    """
    require_platform_admin(user)
    expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)
    token = secrets.token_urlsafe(32)

    with connect() as conn:
        organization = conn.execute(
            "select id, slug from organizations where id = %s",
            (tenant_organization_id,),
        ).fetchone()
        if not organization or organization["slug"] != "eg":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organização da agência não encontrada.",
            )

        if payload.team_id:
            team = conn.execute(
                "select id from teams where id = %s and tenant_organization_id = %s and status = 'active'",
                (payload.team_id, tenant_organization_id),
            ).fetchone()
            if not team:
                # 422 e não 404: o convite é válido, a equipe é que não bate —
                # e quem está convidando precisa saber qual dos dois corrigir.
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Equipe não encontrada nesta organização.",
                )

        allowed_domains = get_settings().invite_allowed_domain_list
        if payload.email and allowed_domains:
            domain = payload.email.rsplit("@", 1)[-1].lower()
            if domain not in allowed_domains:
                # 422 com a lista: quem digitou errado corrige na hora, e quem
                # quis convidar alguem de fora descobre que a regra existe em
                # vez de so ver "erro".
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Convite ao time só para os domínios da EG: "
                        f"{', '.join(allowed_domains)}. Recebido: @{domain}."
                    ),
                )

        if payload.email and invites_repo.find_user_by_email(conn, payload.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este e-mail já tem conta. Adicione a pessoa à equipe em vez de convidar.",
            )

        invite_id = invites_repo.create_invite(
            conn,
            tenant_organization_id,
            payload.email,
            hash_session_token(token),
            expires_at,
            user.id,
            role=payload.role,
            team_id=payload.team_id,
            tenant_role=payload.tenant_role,
        )
        client_hub_repo.write_audit(
            conn,
            user.id,
            tenant_organization_id,
            "invite.created",
            {
                "invite_id": str(invite_id),
                "email": payload.email,
                "scope": "team",
                "team_id": str(payload.team_id) if payload.team_id else None,
            },
        )

    return InviteCreatedResponse(
        id=invite_id,
        token=token,
        path=f"/convite/{token}",
        email=payload.email,
        expires_at=expires_at,
    )


def list_team_invites(tenant_organization_id: UUID, user: CurrentUserResponse) -> list[InviteSummary]:
    require_platform_admin(user)
    with connect() as conn:
        rows = invites_repo.list_invites(conn, tenant_organization_id)
    return [InviteSummary(**row) for row in rows if row.get("role") in ("eg_admin", "eg_member")]


def revoke_team_invite(
    tenant_organization_id: UUID, invite_id: UUID, user: CurrentUserResponse
) -> list[InviteSummary]:
    require_platform_admin(user)
    with connect() as conn:
        invites_repo.delete_invite(conn, tenant_organization_id, invite_id)
    return list_team_invites(tenant_organization_id, user)


def list_invites(client_id: UUID, user: CurrentUserResponse) -> list[InviteSummary]:
    require_platform_admin(user)
    with connect() as conn:
        client = _accessible_client(conn, client_id, user)
        rows = invites_repo.list_invites(conn, client["organization_id"])
    return [InviteSummary(**row) for row in rows]


def revoke_invite(client_id: UUID, invite_id: UUID, user: CurrentUserResponse) -> list[InviteSummary]:
    require_platform_admin(user)
    with connect() as conn:
        client = _accessible_client(conn, client_id, user)
        if not invites_repo.delete_invite(conn, client["organization_id"], invite_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Convite não encontrado ou já utilizado.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "invite.revoked",
            {"client_id": str(client_id), "invite_id": str(invite_id)},
        )
    return list_invites(client_id, user)


def get_invite_public(token: str) -> InvitePublicResponse:
    with connect() as conn:
        invite = invites_repo.find_valid_invite(conn, hash_session_token(token))
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Convite inválido, expirado ou já utilizado.")
    return InvitePublicResponse(
        client_name=invite["client_name"] or invite["organization_name"],
        organization_name=invite["organization_name"],
        email=invite["email"],
        expires_at=invite["expires_at"],
        team_name=invite.get("team_name"),
    )


def accept_invite(token: str, payload: InviteAcceptRequest) -> tuple[str, datetime, UUID]:
    """Cria usuário + membership a partir do convite e abre sessão.

    Retorna (session_token, expires_at, user_id) para o router setar o cookie.
    """
    settings = get_settings()
    with connect() as conn:
        invite = invites_repo.find_valid_invite(conn, hash_session_token(token))
        if not invite:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Convite inválido, expirado ou já utilizado.")

        if invites_repo.find_user_by_email(conn, payload.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este e-mail já possui conta. Entre pelo login ou peça um novo acesso à EG.",
            )

        user_id = invites_repo.create_user(
            conn,
            payload.email,
            payload.display_name.strip(),
            hash_password(payload.password),
        )
        # O convite carrega o que concede. Convite de cliente segue idêntico
        # (`role` nasce 'client_user'); convite de time entra na organização da
        # EG e já cai na equipe, para a pessoa não chegar sem lugar nenhum.
        role = invite.get("role") or "client_user"
        invites_repo.create_membership(conn, user_id, invite["organization_id"], role)
        if role in ("eg_admin", "eg_member"):
            if invite.get("tenant_role"):
                invites_repo.add_tenant_membership(
                    conn, invite["organization_id"], user_id, invite["tenant_role"]
                )
            if invite.get("team_id"):
                invites_repo.add_to_team(conn, invite["team_id"], user_id)
        invites_repo.mark_invite_used(conn, invite["id"], user_id)

        session_token = new_session_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)
        invites_repo.create_session(conn, user_id, hash_session_token(session_token), expires_at)

        client_hub_repo.write_audit(
            conn,
            user_id,
            invite["organization_id"],
            "invite.accepted",
            {"invite_id": str(invite["id"]), "email": payload.email},
        )

    return session_token, expires_at, user_id


def _accessible_client(conn, client_id: UUID, user: CurrentUserResponse):
    # Convite só faz sentido em workspace de cliente; o interno da agência não é convidável.
    return resolve_accessible_client(conn, client_id, user, require_kind="client")
