from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from bioma_api.auth import current_user_from_request, session_cookie_kwargs, user_from_session_token
from bioma_api.config import get_settings
from bioma_api.db import connect
from bioma_api.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    PersonalAccessTokenCreateRequest,
    PersonalAccessTokenCreatedResponse,
    PersonalAccessTokenSummary,
)
from bioma_api.security import hash_session_token, new_personal_access_token, new_session_token, verify_password
from bioma_api.services import rate_limit


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response) -> LoginResponse:
    settings = get_settings()
    email = payload.email.lower()
    recent_failures = rate_limit.assert_login_allowed(request, email)

    with connect() as conn:
        user = conn.execute(
            """
            select id, email, display_name, password_hash
            from users
            where lower(email) = %s and is_active = true
            """,
            (email,),
        ).fetchone()

        credentials_ok = bool(user) and verify_password(payload.password, user["password_hash"])

    # Fora do `with`: o bloco acima faz rollback ao propagar a exceção, e o
    # registro da tentativa precisa sobreviver ao 401 para o limite contar.
    if not credentials_ok:
        rate_limit.record_failed_login(request, email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
        )

    if recent_failures:
        rate_limit.clear_failed_login(request, email)

    with connect() as conn:
        token = new_session_token()
        token_hash = hash_session_token(token)
        ttl_hours = 30 * 24 if payload.remember_me else settings.session_ttl_hours
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

        conn.execute(
            """
            insert into sessions (user_id, token_hash, expires_at, user_agent, last_seen_at)
            values (%s, %s, %s, %s, now())
            """,
            # Cortado em 400: o user-agent é dado do cliente e entra num campo
            # de texto livre — sem limite, um header gigante vira lixo no banco.
            (user["id"], token_hash, expires_at, (request.headers.get("user-agent") or "")[:400] or None),
        )
        conn.execute(
            """
            insert into audit_logs (actor_user_id, event_type, metadata)
            values (%s, 'auth.login', jsonb_build_object('email', %s::text))
            """,
            (user["id"], email),
        )

    response.set_cookie(value=token, **session_cookie_kwargs(expires_at))
    return LoginResponse(user=user_from_session_token(token), expires_at=expires_at)


@router.post("/logout")
def logout(request: Request, response: Response) -> dict[str, str]:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        with connect() as conn:
            conn.execute(
                "update sessions set revoked_at = now() where token_hash = %s and revoked_at is null",
                (hash_session_token(token),),
            )
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        domain=settings.session_cookie_domain,
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_samesite,
    )
    return {"status": "ok"}


@router.get("/me", response_model=CurrentUserResponse)
def me(user: CurrentUserResponse = Depends(current_user_from_request)) -> CurrentUserResponse:
    return user


def _device_label(user_agent: str | None) -> str:
    """Rótulo legível a partir do user-agent.

    Deliberadamente raso: reconhece os casos que a EG usa e devolve o texto
    cru (cortado) para o resto. Trazer uma biblioteca de parsing de UA para
    isto seria custo desproporcional, e um rótulo errado com cara de certo é
    pior que o texto original — quem está revogando acesso precisa reconhecer
    o próprio aparelho, não ler um palpite.
    """
    if not user_agent:
        # Sessão criada antes desta coluna existir. Dizer isso é melhor que
        # rotular como "Navegador Web" e fingir que sabemos.
        return "Origem não registrada (sessão antiga)"
    if user_agent == "testclient":
        return "Teste automatizado (smoke)"

    browser = next(
        (name for marker, name in (
            ("Edg/", "Edge"), ("OPR/", "Opera"), ("Chrome/", "Chrome"),
            ("Firefox/", "Firefox"), ("Safari/", "Safari"),
        ) if marker in user_agent),
        None,
    )
    system = next(
        (name for marker, name in (
            ("Windows", "Windows"), ("Android", "Android"), ("iPhone", "iPhone"),
            ("iPad", "iPad"), ("Mac OS X", "macOS"), ("Linux", "Linux"),
        ) if marker in user_agent),
        None,
    )
    if browser and system:
        return f"{browser} no {system}"
    if browser or system:
        return browser or system or ""
    return user_agent[:60]


@router.get("/sessions")
def list_sessions(
    request: Request,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[dict[str, object]]:
    settings = get_settings()
    current_token = request.cookies.get(settings.session_cookie_name)
    current_hash = hash_session_token(current_token) if current_token else None

    with connect() as conn:
        rows = conn.execute(
            """
            select id, created_at, expires_at, token_hash, user_agent, last_seen_at
            from sessions
            where user_id = %s
              and revoked_at is null
              and expires_at > now()
            order by coalesce(last_seen_at, created_at) desc
            """,
            (user.id,),
        ).fetchall()

    return [
        {
            "id": str(row["id"]),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
            "last_seen_at": row["last_seen_at"].isoformat() if row["last_seen_at"] else None,
            "device_label": _device_label(row["user_agent"]),
            "is_current": current_hash is not None and row["token_hash"] == current_hash,
        }
        for row in rows
    ]


@router.delete("/sessions/other")
def revoke_other_sessions(
    request: Request,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> dict[str, str]:
    settings = get_settings()
    current_token = request.cookies.get(settings.session_cookie_name)
    current_hash = hash_session_token(current_token) if current_token else None

    with connect() as conn:
        if current_hash:
            conn.execute(
                """
                update sessions
                set revoked_at = now()
                where user_id = %s
                  and token_hash != %s
                  and revoked_at is null
                """,
                (user.id, current_hash),
            )
        else:
            conn.execute(
                "update sessions set revoked_at = now() where user_id = %s and revoked_at is null",
                (user.id,),
            )
    return {"status": "ok"}


@router.delete("/sessions/{session_id}")
def revoke_session(
    session_id: str,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> dict[str, str]:
    with connect() as conn:
        conn.execute(
            """
            update sessions
            set revoked_at = now()
            where id = %s::uuid and user_id = %s and revoked_at is null
            """,
            (session_id, user.id),
        )
    return {"status": "ok"}


@router.get("/personal-access-tokens", response_model=list[PersonalAccessTokenSummary])
def list_personal_access_tokens(
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[PersonalAccessTokenSummary]:
    with connect() as conn:
        rows = conn.execute(
            """
            select id, name, token_prefix, last_used_at, expires_at, created_at
            from personal_access_tokens
            where user_id = %s and revoked_at is null
            order by created_at desc
            """,
            (user.id,),
        ).fetchall()
    return [PersonalAccessTokenSummary(**row) for row in rows]


@router.post("/personal-access-tokens", response_model=PersonalAccessTokenCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_personal_access_token(
    payload: PersonalAccessTokenCreateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> PersonalAccessTokenCreatedResponse:
    token = new_personal_access_token()
    token_hash = hash_session_token(token)
    token_prefix = token[:16]
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)
        if payload.expires_in_days
        else None
    )

    with connect() as conn:
        row = conn.execute(
            """
            insert into personal_access_tokens (user_id, name, token_hash, token_prefix, expires_at)
            values (%s, %s, %s, %s, %s)
            returning id, name, token_prefix, last_used_at, expires_at, created_at
            """,
            (user.id, payload.name.strip(), token_hash, token_prefix, expires_at),
        ).fetchone()
        conn.execute(
            """
            insert into audit_logs (actor_user_id, event_type, metadata)
            values (%s, 'auth.personal_access_token.created', jsonb_build_object('name', %s::text))
            """,
            (user.id, payload.name.strip()),
        )

    return PersonalAccessTokenCreatedResponse(token=token, summary=PersonalAccessTokenSummary(**row))


@router.delete("/personal-access-tokens/{token_id}")
def revoke_personal_access_token(
    token_id: str,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> dict[str, str]:
    with connect() as conn:
        conn.execute(
            """
            update personal_access_tokens
            set revoked_at = now()
            where id = %s::uuid and user_id = %s and revoked_at is null
            """,
            (token_id, user.id),
        )
    return {"status": "ok"}
