import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (InvalidHashError, VerifyMismatchError):
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_personal_access_token() -> str:
    # Prefixo reconhecível (padrão GitHub/Stripe) — ajuda a identificar o
    # segredo em logs/scanners antes mesmo de saber que é do Bioma.
    return f"bioma_pat_{secrets.token_urlsafe(40)}"
