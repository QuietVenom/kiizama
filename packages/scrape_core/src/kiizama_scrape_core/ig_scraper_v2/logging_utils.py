from __future__ import annotations

import re
from typing import Any

_AUTH_HEADER_RE = re.compile(r"(?i)(authorization\s*[:=]\s*)(bearer\s+)?[^\s,;)}\]]+")
_COOKIE_HEADER_RE = re.compile(
    r"(?i)(cookie\s*[:=]\s*).*?"
    r"(?=\s+(?:authorization|proxy(?:_url|_urls)?|server|password|passwd|pwd|"
    r"token|api[_-]?key|secret)\s*[:=]|$)"
)
_SECRET_PAIR_RE = re.compile(
    r"(?i)\b(sessionid|csrftoken|password|passwd|pwd|token|api[_-]?key|secret)"
    r"\s*[:=]\s*([^;\s,)}\]]+)"
)
_PROXY_PAIR_RE = re.compile(
    r"(?i)\b(proxy(?:_url|_urls)?|server)\s*[:=]\s*([^;\s,)}\]]+)"
)
_URL_WITH_USERINFO_RE = re.compile(r"([a-z][a-z0-9+.-]*://)([^/@\s]+)@")


def redacted_identifier(value: str | None) -> str:
    if not value:
        return "unknown"
    normalized = str(value).strip()
    if len(normalized) <= 8:
        return "***"
    if "-" in normalized and len(normalized) >= 20:
        first, *_, last = normalized.split("-")
        return f"{first}-...-{last}"
    return f"{normalized[:4]}...{normalized[-4:]}"


def redacted_login_username(value: str | None) -> str:
    if not value:
        return "unknown"
    normalized = str(value).strip()
    if not normalized:
        return "unknown"
    if "@" not in normalized:
        return f"{normalized[0]}***"
    local_part, domain = normalized.split("@", 1)
    first = local_part[0] if local_part else "*"
    return f"{first}***@{domain}"


def sanitize_log_value(value: Any) -> str:
    text = str(value)
    text = _URL_WITH_USERINFO_RE.sub(r"\1<redacted>@", text)
    text = _AUTH_HEADER_RE.sub(r"\1<redacted>", text)
    text = _COOKIE_HEADER_RE.sub(r"\1<redacted>", text)
    text = _SECRET_PAIR_RE.sub(lambda match: f"{match.group(1)}=<redacted>", text)
    text = _PROXY_PAIR_RE.sub(lambda match: f"{match.group(1)}=<redacted>", text)
    return text


def sanitize_exception_for_log(exc: Exception) -> str:
    sanitized = sanitize_log_value(exc)
    try:
        exc.args = (sanitized,)
    except Exception:
        pass
    return sanitized


def proxy_mode_label(config: Any) -> str:
    proxy = getattr(config, "proxy", None)
    return "decodo" if getattr(proxy, "use_isp_proxy", False) else "local"


def format_counters(counters: Any) -> str:
    return (
        f"requested={int(getattr(counters, 'requested', 0) or 0)} "
        f"successful={int(getattr(counters, 'successful', 0) or 0)} "
        f"failed={int(getattr(counters, 'failed', 0) or 0)} "
        f"not_found={int(getattr(counters, 'not_found', 0) or 0)}"
    )


__all__ = [
    "format_counters",
    "proxy_mode_label",
    "redacted_identifier",
    "redacted_login_username",
    "sanitize_exception_for_log",
    "sanitize_log_value",
]
