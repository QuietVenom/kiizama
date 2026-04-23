from datetime import timedelta

import jwt

from app.core import security
from app.core.config import settings


def test_create_access_token_encodes_subject_expiration_and_additional_claims() -> None:
    token = security.create_access_token(
        subject="user-1",
        expires_delta=timedelta(minutes=5),
        additional_claims={"principal_type": "user", "role": "member"},
    )

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])

    assert payload["sub"] == "user-1"
    assert payload["principal_type"] == "user"
    assert payload["role"] == "member"
    assert "exp" in payload


def test_password_hash_round_trip_verifies_and_rejects_wrong_password() -> None:
    hashed = security.get_password_hash("SafePass1!")

    assert hashed != "SafePass1!"
    assert security.verify_password("SafePass1!", hashed) is True
    assert security.verify_password("WrongPass1!", hashed) is False
