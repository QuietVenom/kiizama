import hashlib
import hmac
import time

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.features.billing.clients.stripe import verify_stripe_signature


def _signature_header(*, payload: bytes, secret: str, timestamp: int) -> str:
    signed_payload = f"{timestamp}.".encode() + payload
    signature = hmac.new(
        secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


def test_verify_stripe_signature_rejects_missing_v1(monkeypatch) -> None:
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")

    with pytest.raises(HTTPException) as exc_info:
        verify_stripe_signature(
            payload=b"{}",
            signature_header=f"t={int(time.time())}",
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid Stripe signature."


def test_verify_stripe_signature_rejects_expired_timestamp(monkeypatch) -> None:
    secret = "whsec_test"
    payload = b'{"id":"evt_expired"}'
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", secret)

    expired_timestamp = int(time.time()) - 1_000
    with pytest.raises(HTTPException) as exc_info:
        verify_stripe_signature(
            payload=payload,
            signature_header=_signature_header(
                payload=payload,
                secret=secret,
                timestamp=expired_timestamp,
            ),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Expired Stripe signature."


def test_verify_stripe_signature_returns_503_when_secret_missing(monkeypatch) -> None:
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", None)

    with pytest.raises(HTTPException) as exc_info:
        verify_stripe_signature(
            payload=b"{}",
            signature_header="t=123,v1=deadbeef",
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Stripe webhook secret is not configured."
