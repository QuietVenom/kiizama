from __future__ import annotations

import asyncio

from starlette.requests import Request

from app.features.rate_limit.keys import build_rate_limit_key
from app.features.rate_limit.policies import POLICIES
from app.features.rate_limit.schemas import RateLimitSubjectKind
from app.features.rate_limit.subjects import (
    get_client_ip,
    normalize_email,
    resolve_subject,
)


def _request(
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
    path_params: dict[str, str] | None = None,
    json_body: bytes = b"",
) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/test",
        "headers": headers or [],
        "client": ("10.0.0.5", 1234),
        "path_params": path_params or {},
    }

    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": json_body, "more_body": False}

    return Request(scope, receive)


def test_get_client_ip_prefers_first_forwarded_value() -> None:
    request = _request(
        headers=[(b"x-forwarded-for", b" 203.0.113.10, 198.51.100.8")],
    )
    assert get_client_ip(request) == "203.0.113.10"


def test_resolve_email_normalizes_path_param() -> None:
    request = _request(path_params={"email": "User@Example.COM "})
    subject = asyncio.run(
        resolve_subject(
            request,
            policy=POLICIES.public_auth_password_recovery,
            subject_kind=RateLimitSubjectKind.EMAIL,
        )
    )
    assert subject == "user@example.com"


def test_resolve_ip_email_uses_json_body_and_ip() -> None:
    request = _request(
        headers=[(b"x-forwarded-for", b"203.0.113.9")],
        json_body=b'{"email":"User@Example.com"}',
    )
    subject = asyncio.run(
        resolve_subject(
            request,
            policy=POLICIES.public_auth_password_recovery,
            subject_kind=RateLimitSubjectKind.IP_EMAIL,
        )
    )
    assert subject == "203.0.113.9:user@example.com"


def test_build_rate_limit_key_hashes_sensitive_values() -> None:
    key = build_rate_limit_key(
        policy_name="public_auth_password_recovery",
        subject="203.0.113.9:user@example.com",
    )
    assert key.startswith("rl:v1:public_auth_password_recovery:")
    assert "user@example.com" not in key
    assert "203.0.113.9" not in key


def test_normalize_email_strips_and_lowercases() -> None:
    assert normalize_email(" User@Example.COM ") == "user@example.com"
