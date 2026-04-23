from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, cast

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

from ..constants import STRIPE_SIGNATURE_TOLERANCE_SECONDS

StripeRequestPayload = dict[str, str]


def _stripe_headers() -> dict[str, str]:
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured.",
        )
    return {"Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}"}


async def _stripe_request_raw(
    method: str,
    path: str,
    *,
    data: StripeRequestPayload | None = None,
    params: StripeRequestPayload | None = None,
    extra_headers: dict[str, str] | None = None,
) -> httpx.Response:
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        **_stripe_headers(),
    }
    if extra_headers:
        headers.update(extra_headers)
    async with httpx.AsyncClient(
        base_url=settings.STRIPE_API_BASE,
        timeout=20.0,
    ) as client:
        return await client.request(
            method,
            path,
            data=data,
            params=params,
            headers=headers,
        )


def _extract_stripe_error_message(response: httpx.Response) -> str:
    try:
        payload = cast(dict[str, Any], response.json())
    except ValueError:
        payload = {}
    error = cast(dict[str, Any], payload.get("error") or {})
    message = str(error.get("message") or "").strip()
    if message:
        return message
    return "Stripe request failed."


async def _stripe_request(
    method: str,
    path: str,
    *,
    data: StripeRequestPayload | None = None,
    params: StripeRequestPayload | None = None,
) -> dict[str, Any]:
    response = await _stripe_request_raw(
        method,
        path,
        data=data,
        params=params,
    )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_extract_stripe_error_message(response),
        )
    return cast(dict[str, Any], response.json())


async def set_subscription_cancel_at_period_end(
    *,
    stripe_subscription_id: str,
    cancel_at_period_end: bool,
) -> None:
    await _stripe_request(
        "POST",
        f"/v1/subscriptions/{stripe_subscription_id}",
        data={"cancel_at_period_end": "true" if cancel_at_period_end else "false"},
    )


async def cancel_stripe_subscription_immediately(
    *,
    stripe_subscription_id: str,
) -> None:
    await _stripe_request("DELETE", f"/v1/subscriptions/{stripe_subscription_id}")


async def delete_stripe_customer(stripe_customer_id: str) -> None:
    await _stripe_request("DELETE", f"/v1/customers/{stripe_customer_id}")


def verify_stripe_signature(*, payload: bytes, signature_header: str) -> None:
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook secret is not configured.",
        )
    parts = [item.strip() for item in signature_header.split(",") if item.strip()]
    timestamp: int | None = None
    signatures: list[str] = []
    for part in parts:
        key, _, value = part.partition("=")
        if key == "t":
            try:
                timestamp = int(value)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Stripe signature.",
                ) from exc
        elif key == "v1":
            signatures.append(value)
    if timestamp is None or not signatures:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe signature.",
        )
    if abs(int(time.time()) - timestamp) > STRIPE_SIGNATURE_TOLERANCE_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expired Stripe signature.",
        )
    signed_payload = str(timestamp).encode() + b"." + payload
    expected = hmac.new(
        settings.STRIPE_WEBHOOK_SECRET.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    if not any(hmac.compare_digest(expected, item) for item in signatures):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe signature.",
        )


async def fetch_stripe_subscription(subscription_id: str) -> dict[str, Any]:
    return await _stripe_request(
        "GET",
        f"/v1/subscriptions/{subscription_id}",
        params={"expand[]": "latest_invoice"},
    )


async def fetch_stripe_invoice(invoice_id: str) -> dict[str, Any]:
    return await _stripe_request(
        "GET",
        f"/v1/invoices/{invoice_id}",
    )


async def fetch_stripe_charge(charge_id: str) -> dict[str, Any]:
    return await _stripe_request(
        "GET",
        f"/v1/charges/{charge_id}",
        params={"expand[]": "invoice"},
    )


__all__ = [
    "StripeRequestPayload",
    "_extract_stripe_error_message",
    "_stripe_headers",
    "_stripe_request",
    "_stripe_request_raw",
    "cancel_stripe_subscription_immediately",
    "delete_stripe_customer",
    "fetch_stripe_charge",
    "fetch_stripe_invoice",
    "fetch_stripe_subscription",
    "set_subscription_cancel_at_period_end",
    "verify_stripe_signature",
]
