"""Cifra de segredos em repouso (Fernet/AES-128-CBC+HMAC).

Regra do projeto desde o port do BIAds: nenhum segredo de integração em
texto puro no banco (LGPD). Chave em SECRET_ENCRYPTION_KEY (env), gerada com:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Formato armazenado: ``enc:v1:<token-fernet>``. Valores sem o prefixo são
tratados como legado em texto puro no decrypt (linhas antigas do Kommo) e
serão cifrados na próxima gravação.
"""

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status

from bioma_api.config import get_settings

_PREFIX = "enc:v1:"


class EncryptionNotConfiguredError(Exception):
    pass


def _fernet() -> Fernet:
    settings = get_settings()
    if not settings.secret_encryption_key:
        raise EncryptionNotConfiguredError(
            "SECRET_ENCRYPTION_KEY ausente — configure antes de armazenar segredos."
        )
    return Fernet(settings.secret_encryption_key.encode("utf-8"))


def encrypt_secret(value: str) -> str:
    return _PREFIX + _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    if not value.startswith(_PREFIX):
        # Legado (gravado antes da cifra): devolve como está.
        return value
    try:
        return _fernet().decrypt(value[len(_PREFIX):].encode("utf-8")).decode("utf-8")
    except InvalidToken as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao decifrar segredo (SECRET_ENCRYPTION_KEY trocada?).",
        ) from error


def require_encryption_configured() -> None:
    settings = get_settings()
    if not settings.secret_encryption_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Armazenamento de segredos indisponível: configure SECRET_ENCRYPTION_KEY no ambiente.",
        )
