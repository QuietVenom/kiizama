from __future__ import annotations

import ipaddress
import json
from functools import lru_cache
from typing import Any, cast

from fastapi import HTTPException, Request

from app.api.deps import _decode_token_payload

from .schemas import RateLimitPolicy, RateLimitSubjectKind


@lru_cache(maxsize=1)
def _token_header_prefixes() -> tuple[str, ...]:
    return ("bearer ",)


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_ip(value: str) -> str:
    ip = ipaddress.ip_address(value.strip())
    return ip.compressed


def get_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    candidates: list[str] = []
    if forwarded_for:
        candidates.extend(part.strip() for part in forwarded_for.split(","))
    if request.client and request.client.host:
        candidates.append(request.client.host)

    for candidate in candidates:
        if not candidate:
            continue
        try:
            return normalize_ip(candidate)
        except ValueError:
            continue
    return None


async def _get_request_json(request: Request) -> dict[str, Any]:
    cached = getattr(request.state, "_rate_limit_json", None)
    if cached is not None:
        return cast(dict[str, Any], cached)
    try:
        payload = await request.json()
    except (json.JSONDecodeError, RuntimeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    request.state._rate_limit_json = payload
    return cast(dict[str, Any], payload)


async def _get_request_form(request: Request) -> dict[str, Any]:
    cached = getattr(request.state, "_rate_limit_form", None)
    if cached is not None:
        return cast(dict[str, Any], cached)
    try:
        form = await request.form()
    except HTTPException:
        payload: dict[str, Any] = {}
    else:
        payload = dict(form)
    request.state._rate_limit_form = payload
    return payload


def _get_path_value(request: Request, name: str) -> str | None:
    value = request.path_params.get(name)
    return value if isinstance(value, str) and value.strip() else None


async def _get_email(request: Request) -> str | None:
    path_email = _get_path_value(request, "email")
    if path_email:
        return normalize_email(path_email)

    payload = await _get_request_json(request)
    email = payload.get("email")
    if isinstance(email, str) and email.strip():
        return normalize_email(email)

    return None


async def _get_username(request: Request) -> str | None:
    form = await _get_request_form(request)
    username = form.get("username")
    if isinstance(username, str) and username.strip():
        return normalize_email(username)
    return None


def _get_user_id(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if not authorization:
        return None
    for prefix in _token_header_prefixes():
        if authorization.lower().startswith(prefix):
            token = authorization[len(prefix) :].strip()
            if not token:
                return None
            try:
                payload = _decode_token_payload(token)
            except HTTPException:
                return None
            if payload.principal_type == "admin":
                return None
            return str(payload.sub)
    return None


async def resolve_subject(
    request: Request,
    *,
    policy: RateLimitPolicy,
    subject_kind: RateLimitSubjectKind,
) -> str | None:
    del policy

    if subject_kind is RateLimitSubjectKind.IP:
        return get_client_ip(request)

    if subject_kind is RateLimitSubjectKind.USER_ID:
        return _get_user_id(request)

    if subject_kind is RateLimitSubjectKind.EMAIL:
        return await _get_email(request)

    if subject_kind is RateLimitSubjectKind.IP_EMAIL:
        ip = get_client_ip(request)
        email = await _get_email(request)
        if ip and email:
            return f"{ip}:{email}"
        return None

    if subject_kind is RateLimitSubjectKind.IP_USERNAME:
        ip = get_client_ip(request)
        username = await _get_username(request)
        if ip and username:
            return f"{ip}:{username}"
        return None

    return None
