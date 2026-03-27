from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


def _derive_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def resolve_ig_credentials_secret(
    secret_key: str | None = None,
    *,
    env_var: str = "SECRET_KEY_IG_CREDENTIALS",
) -> str:
    candidate = secret_key if secret_key is not None else os.getenv(env_var)
    if candidate and candidate.strip():
        return candidate.strip()
    raise ValueError(f"{env_var} is required.")


def _get_fernet(secret_key: str | None = None) -> Fernet:
    return Fernet(_derive_key(resolve_ig_credentials_secret(secret_key)))


def encrypt_ig_password(
    plain_password: str,
    *,
    secret_key: str | None = None,
) -> str:
    if not plain_password:
        return plain_password
    token = _get_fernet(secret_key).encrypt(plain_password.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_ig_password(
    encrypted_password: str,
    *,
    secret_key: str | None = None,
) -> str:
    if not encrypted_password:
        return encrypted_password
    try:
        value = _get_fernet(secret_key).decrypt(encrypted_password.encode("utf-8"))
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted Instagram password.") from exc
    return value.decode("utf-8")


def encrypt_ig_session(
    session: dict[str, Any] | None,
    *,
    secret_key: str | None = None,
) -> str | None:
    if session is None:
        return None
    payload = json.dumps(
        session,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return encrypt_ig_password(payload, secret_key=secret_key)


def decrypt_ig_session(
    encrypted_session: str | None,
    *,
    secret_key: str | None = None,
) -> dict[str, Any] | None:
    if not encrypted_session:
        return None
    payload = decrypt_ig_password(encrypted_session, secret_key=secret_key)
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Invalid encrypted Instagram session payload.")
    return data


__all__ = [
    "decrypt_ig_password",
    "decrypt_ig_session",
    "encrypt_ig_password",
    "encrypt_ig_session",
    "resolve_ig_credentials_secret",
]
