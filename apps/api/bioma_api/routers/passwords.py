from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from bioma_api.auth import current_user_from_request, session_cookie_kwargs, user_from_session_token
from bioma_api.config import get_settings
from bioma_api.schemas.auth import (
    CurrentUserResponse,
    LoginResponse,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetCreatedResponse,
    PasswordResetCreateRequest,
    PasswordResetPublicResponse,
)
from bioma_api.services import passwords as passwords_service


router = APIRouter(prefix="/auth", tags=["passwords"])


@router.post("/password")
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> dict[str, int | str]:
    settings = get_settings()
    session_token = request.cookies.get(settings.session_cookie_name)
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão ausente.")
    revoked = passwords_service.change_password(user, payload, session_token)
    return {"status": "ok", "revoked_sessions": revoked}


@router.post("/password-resets", response_model=PasswordResetCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_reset(
    payload: PasswordResetCreateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> PasswordResetCreatedResponse:
    return passwords_service.create_reset(payload, user)


@router.get("/password-resets/{token}", response_model=PasswordResetPublicResponse)
def get_reset(token: str) -> PasswordResetPublicResponse:
    return passwords_service.get_reset_public(token)


@router.post("/password-resets/{token}/confirm", response_model=LoginResponse)
def confirm_reset(token: str, payload: PasswordResetConfirmRequest, response: Response) -> LoginResponse:
    session_token, expires_at = passwords_service.confirm_reset(token, payload.password)
    response.set_cookie(value=session_token, **session_cookie_kwargs(expires_at))
    return LoginResponse(user=user_from_session_token(session_token), expires_at=expires_at)
