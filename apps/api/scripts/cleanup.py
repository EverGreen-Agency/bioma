"""Limpeza de dados transitórios (item de retenção do LGPD-001).

Remove o que já não tem função e só acumula dado pessoal/técnico:
- sessões expiradas ou revogadas há mais de 7 dias;
- convites usados ou expirados há mais de 30 dias;
- resets de senha usados ou expirados há mais de 30 dias;
- tentativas de login fora da janela do rate limit (SEC-003).

Roda no boot da API (scripts/start.py) e pode ser executado manualmente:
    python scripts/cleanup.py
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bioma_api.config import get_settings  # noqa: E402
from bioma_api.db import connect  # noqa: E402
from bioma_api.repositories import rate_limit as rate_limit_repo  # noqa: E402


def run_cleanup(conn) -> dict[str, int]:
    sessions = conn.execute(
        """
        delete from sessions
        where expires_at < now() - interval '7 days'
           or revoked_at < now() - interval '7 days'
           -- Abandonada: a renovação rolante estende o prazo de toda sessão em
           -- uso, então "expirou" nunca alcançava as que ninguém usa mais. Sem
           -- esta linha elas se acumulavam para sempre e entupiam a tela de
           -- dispositivos autorizados (chegou a 1006 para um usuário).
           or (coalesce(last_seen_at, created_at) < now() - interval '30 days')
           -- Login de smoke não é dispositivo de ninguém.
           or (user_agent = 'testclient' and created_at < now() - interval '1 day')
        returning id
        """
    ).fetchall()
    invites = conn.execute(
        """
        delete from invites
        where (used_at is not null and used_at < now() - interval '30 days')
           or (used_at is null and expires_at < now() - interval '30 days')
        returning id
        """
    ).fetchall()
    resets = conn.execute(
        """
        delete from password_resets
        where (used_at is not null and used_at < now() - interval '30 days')
           or (used_at is null and expires_at < now() - interval '30 days')
        returning id
        """
    ).fetchall()
    # Guarda uma folga sobre a janela para não apagar tentativa ainda contável.
    login_attempts = rate_limit_repo.purge_expired(
        conn, get_settings().login_rate_limit_window_seconds * 2
    )
    return {
        "sessions": len(sessions),
        "invites": len(invites),
        "password_resets": len(resets),
        "login_attempts": login_attempts,
    }


def main() -> None:
    with connect() as conn:
        removed = run_cleanup(conn)
    print(f"cleanup ok: {removed}")


if __name__ == "__main__":
    main()
