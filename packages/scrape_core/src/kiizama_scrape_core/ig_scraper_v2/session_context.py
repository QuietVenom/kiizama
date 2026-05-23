from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .config import ScraperV2Config
from .constants import DEFAULT_USER_AGENT


@dataclass(frozen=True, slots=True)
class EffectiveSessionContext:
    config: ScraperV2Config
    storage_state: dict[str, Any] | None
    extra_http_headers: dict[str, str]


def build_effective_session_context(
    config: ScraperV2Config,
    raw_state: dict[str, Any] | None,
) -> EffectiveSessionContext:
    storage_state = dict(raw_state) if raw_state else None
    headers, session_user_agent, session_locale = extract_session_info(
        storage_state or {}
    )
    extra_headers = {
        key: value
        for key, value in headers.items()
        if key.lower() not in {"cookie", "user-agent"}
    }

    browser_config = config.browser
    if session_user_agent and browser_config.user_agent == DEFAULT_USER_AGENT:
        browser_config = replace(browser_config, user_agent=session_user_agent)
    if session_locale:
        browser_config = replace(browser_config, locale=session_locale)

    return EffectiveSessionContext(
        config=replace(config, browser=browser_config),
        storage_state=storage_state,
        extra_http_headers=extra_headers,
    )


def extract_session_info(
    raw_state: dict[str, Any],
) -> tuple[dict[str, str], str | None, str | None]:
    headers: dict[str, str] = {}
    user_agent: str | None = None
    locale: str | None = None

    session_metadata = raw_state.get("__session")
    if isinstance(session_metadata, dict):
        raw_headers = session_metadata.get("headers")
        if isinstance(raw_headers, dict):
            headers = {
                str(key): str(value)
                for key, value in raw_headers.items()
                if isinstance(key, str) and isinstance(value, str)
            }

        raw_user_agent = session_metadata.get("user_agent")
        if isinstance(raw_user_agent, str) and raw_user_agent:
            user_agent = raw_user_agent

        raw_locale = session_metadata.get("locale")
        if isinstance(raw_locale, str) and raw_locale:
            locale = raw_locale

    return headers, user_agent, locale


__all__ = [
    "EffectiveSessionContext",
    "build_effective_session_context",
    "extract_session_info",
]
