import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken


def _derive_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _resolve_secret_key() -> str:
    raw_secret = os.getenv("SECRET_KEY_IG_CREDENTIALS")
    if raw_secret and raw_secret.strip():
        return raw_secret.strip()

    # Fallback for existing backend flows that rely on Settings object.
    from app.core.config import settings

    secret = settings.SECRET_KEY_IG_CREDENTIALS
    if not secret.strip():
        raise ValueError("SECRET_KEY_IG_CREDENTIALS is required.")
    return secret.strip()


def _get_fernet() -> Fernet:
    return Fernet(_derive_key(_resolve_secret_key()))


def encrypt_ig_password(plain_password: str) -> str:
    if not plain_password:
        return plain_password
    token = _get_fernet().encrypt(plain_password.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_ig_password(encrypted_password: str) -> str:
    if not encrypted_password:
        return encrypted_password
    try:
        value = _get_fernet().decrypt(encrypted_password.encode("utf-8"))
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted Instagram password.") from exc
    return value.decode("utf-8")
