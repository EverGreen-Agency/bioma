from datetime import datetime, timezone

from fastapi import HTTPException, Request, status

from bioma_api.config import get_settings
from bioma_api.db import connect
from bioma_api.security import hash_session_token
from bioma_api.schemas.auth import CurrentUserResponse, OrganizationSummary


def current_user_from_request(request: Request) -> CurrentUserResponse:
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return _user_from_personal_access_token(auth_header[len("Bearer "):].strip())

    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão ausente.")

    return user_from_session_token(token)


def user_from_session_token(token: str) -> CurrentUserResponse:
    """Resolve o usuário a partir do token de sessão puro.

    Existe separada de `current_user_from_request` porque o /auth/login precisa
    montar a resposta logo após criar a sessão, quando ainda não há um Request
    com o cookie. Antes isso era feito com um objeto falso de Request, que
    quebrava sempre que esta função passava a ler um campo novo (foi o que
    aconteceu ao adicionar o header Authorization dos tokens pessoais).
    """
    token_hash = hash_session_token(token)
    with connect() as conn:
        session = conn.execute(
            """
            select s.user_id, s.expires_at, u.email, u.display_name,
                   u.password_hash is not null as has_password
            from sessions s
            join users u on u.id = s.user_id
            where s.token_hash = %s
              and s.revoked_at is null
              and s.expires_at > now()
              and u.is_active = true
            """,
            (token_hash,),
        ).fetchone()

        if not session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida.")

        # Rolling session: se a sessão restar menos de 15 dias de validade, renova por +30 dias automaticamente
        expires_at = session["expires_at"]
        if expires_at and (expires_at.tzinfo is None or expires_at.tzinfo != timezone.utc):
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at and (expires_at - datetime.now(timezone.utc)).total_seconds() < 15 * 86400:
            conn.execute(
                "update sessions set expires_at = now() + interval '30 days' where token_hash = %s",
                (token_hash,),
            )

        # Marca uso a cada requisição autenticada. É o que permite a faxina
        # apagar sessão abandonada por desuso — antes, a renovação rolante
        # acima garantia que nenhuma sessão em uso expirasse, e a que NÃO
        # estava em uso também não expirava enquanto o prazo não vencesse.
        conn.execute(
            "update sessions set last_seen_at = now() where token_hash = %s",
            (token_hash,),
        )

        return _build_current_user(
            conn, session["user_id"], session["email"], session["display_name"], session["has_password"],
        )


def _user_from_personal_access_token(token: str) -> CurrentUserResponse:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de acesso pessoal ausente.")
    token_hash = hash_session_token(token)
    with connect() as conn:
        pat = conn.execute(
            """
            select p.user_id, u.email, u.display_name, u.password_hash is not null as has_password
            from personal_access_tokens p
            join users u on u.id = p.user_id
            where p.token_hash = %s
              and p.revoked_at is null
              and (p.expires_at is null or p.expires_at > now())
              and u.is_active = true
            """,
            (token_hash,),
        ).fetchone()
        if not pat:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de acesso pessoal inválido, expirado ou revogado.")

        conn.execute(
            "update personal_access_tokens set last_used_at = now() where token_hash = %s",
            (token_hash,),
        )
        return _build_current_user(conn, pat["user_id"], pat["email"], pat["display_name"], pat["has_password"])


def _build_current_user(conn, user_id, email: str, display_name: str, has_password: bool) -> CurrentUserResponse:
    memberships = conn.execute(
        """
        select o.id, o.name, o.slug, m.role, o.enabled_modules
        from memberships m
        join organizations o on o.id = m.organization_id
        where m.user_id = %s
        order by o.type, o.name
        """,
        (user_id,),
    ).fetchall()

    return CurrentUserResponse(
        id=user_id,
        email=email,
        display_name=display_name,
        has_password=has_password,
        organizations=[OrganizationSummary(**row) for row in memberships],
    )


def session_cookie_kwargs(expires_at: datetime) -> dict[str, object]:
    settings = get_settings()
    max_age = max(0, int((expires_at - datetime.now(timezone.utc)).total_seconds()))
    kwargs: dict[str, object] = {
        "key": settings.session_cookie_name,
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.session_cookie_samesite,
        "max_age": max_age,
        "path": "/",
    }
    if settings.session_cookie_domain:
        kwargs["domain"] = settings.session_cookie_domain
    return kwargs
