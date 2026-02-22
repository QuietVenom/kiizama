from __future__ import annotations

import base64
import logging
import re
from mimetypes import guess_type
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}
_FB_CDN_HOST_RE = re.compile(r"^instagram\.[a-z0-9-]+\.fna\.fbcdn\.net$")
_ALLOWED_PROFILE_PIC_HOST_SUFFIXES = (".cdninstagram.com",)


def is_allowed_profile_picture_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme.lower() != "https":
        return False

    host = (parsed.hostname or "").lower()
    if not host:
        return False

    if _FB_CDN_HOST_RE.fullmatch(host):
        return True

    return any(host.endswith(suffix) for suffix in _ALLOWED_PROFILE_PIC_HOST_SUFFIXES)


def resolve_profile_picture_data_uri(
    url: str,
    logger: logging.Logger | None = None,
) -> str | None:
    if not isinstance(url, str) or not url:
        return None
    if not is_allowed_profile_picture_url(url):
        return None

    try:
        request = Request(url, headers=_DEFAULT_HEADERS)
        with urlopen(request, timeout=15) as response:  # nosec: B310
            data = response.read()
            content_type = response.headers.get("Content-Type") or ""
    except URLError as exc:
        if logger:
            logger.debug(
                "No se pudo descargar la foto de perfil %s: %s",
                url,
                exc.reason,
            )
        return url
    except Exception as exc:  # pragma: no cover - defensive runtime fallback
        if logger:
            logger.debug("No se pudo descargar la foto de perfil %s: %s", url, exc)
        return url

    if not data:
        return url

    if ";" in content_type:
        content_type = content_type.split(";", 1)[0].strip()
    if not content_type:
        guessed, _ = guess_type(url)
        content_type = guessed or "image/jpeg"

    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def enrich_profile_picture(
    profile: dict[str, Any],
    logger: logging.Logger | None = None,
    *,
    url_field: str = "profile_pic_url",
    src_field: str = "profile_pic_src",
) -> None:
    url = profile.get(url_field)
    if not isinstance(url, str) or not url:
        return
    if not is_allowed_profile_picture_url(url):
        if logger:
            logger.debug("Bloqueada profile_pic_url no permitida: %s", url)
        profile[url_field] = ""
        return

    data_uri_or_url = resolve_profile_picture_data_uri(url, logger=logger)
    if data_uri_or_url:
        profile[src_field] = data_uri_or_url


__all__ = [
    "enrich_profile_picture",
    "is_allowed_profile_picture_url",
    "resolve_profile_picture_data_uri",
]
