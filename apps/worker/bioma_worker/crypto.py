"""Espelha bioma_api/crypto.py — o worker precisa decifrar (e, ao renovar,
recifrar) tokens OAuth por conexão gravados pela API. Mesma chave
(SECRET_ENCRYPTION_KEY), mesmo formato (``enc:v1:<token-fernet>``)."""

from cryptography.fernet import Fernet, InvalidToken

_PREFIX = "enc:v1:"


def _fernet(secret_encryption_key: str) -> Fernet:
    return Fernet(secret_encryption_key.encode("utf-8"))


def encrypt_secret(value: str, secret_encryption_key: str) -> str:
    return _PREFIX + _fernet(secret_encryption_key).encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None, secret_encryption_key: str) -> str | None:
    if value is None:
        return None
    if not value.startswith(_PREFIX):
        return value
    try:
        return _fernet(secret_encryption_key).decrypt(value[len(_PREFIX):].encode("utf-8")).decode("utf-8")
    except InvalidToken as error:
        raise RuntimeError("Falha ao decifrar token OAuth (SECRET_ENCRYPTION_KEY trocada?).") from error
