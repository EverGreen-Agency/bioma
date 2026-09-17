"""Rate limit de login compartilhado entre réplicas (SEC-003).

Cada função abre a própria conexão de propósito. O caminho do login registra
a tentativa falha e em seguida levanta 401 — se o insert compartilhasse a
transação do handler, o `psycopg.connect` faria rollback ao propagar a
exceção e a tentativa nunca seria contada. Transação separada é o que faz o
limite existir de verdade.
"""

import hashlib

from fastapi import HTTPException, Request, status

from bioma_api.config import get_settings
from bioma_api.db import connect
from bioma_api.repositories import rate_limit as rate_limit_repo


def build_key(request: Request, email: str) -> str:
    """`sha256(ip:email)` — o par em texto nunca vai para o banco (LGPD-001)."""
    host = request.client.host if request.client else "unknown"
    return hashlib.sha256(f"{host}:{email}".encode("utf-8")).hexdigest()


def assert_login_allowed(request: Request, email: str) -> int:
    """Levanta 429 se estourou a janela; devolve quantas tentativas contou.

    O retorno evita um DELETE (e uma conexão) no caminho feliz mais comum, em
    que não há nada a limpar. Conexões por request são item aberto (DB-001).
    """
    settings = get_settings()
    key_hash = build_key(request, email)
    with connect() as conn:
        attempts = rate_limit_repo.count_recent_attempts(
            conn, key_hash, settings.login_rate_limit_window_seconds
        )
    if attempts >= settings.login_rate_limit_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Aguarde e tente novamente.",
        )
    return attempts


def record_failed_login(request: Request, email: str) -> None:
    with connect() as conn:
        rate_limit_repo.record_attempt(conn, build_key(request, email))


def clear_failed_login(request: Request, email: str) -> None:
    with connect() as conn:
        rate_limit_repo.clear_attempts(conn, build_key(request, email))
