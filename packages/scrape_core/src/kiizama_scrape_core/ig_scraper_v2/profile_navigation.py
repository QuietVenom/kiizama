from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .config import ScraperV2Config
from .models import ProfileOpenResult, ProfileOpenStatus

RetryableGoto = Callable[..., Any]

_INSTAGRAM_BASE_URL = "https://www.instagram.com"
_UNAVAILABLE_TEXTS = (
    "profile isn't available",
    "profile no disponible",
    "profile no está disponible",
    "profile not available",
    "sorry, this page isn't available",
    "sorry, this page isn't available.",
    "the link you followed may be broken",
    "this page isn't available",
)
_UNAVAILABLE_RE = re.compile(
    "|".join(re.escape(text) for text in _UNAVAILABLE_TEXTS),
    re.IGNORECASE,
)


class InstagramProfileNavigator:
    def __init__(
        self,
        *,
        config: ScraperV2Config,
        retryable_goto: RetryableGoto,
        logger: logging.Logger | None = None,
    ) -> None:
        self.config = config
        self.retryable_goto = retryable_goto
        self.logger = logger or logging.getLogger(
            "kiizama_scrape_core.ig_scraper_v2.profile_navigation"
        )

    async def open_profile(self, page: Page, username: str) -> ProfileOpenResult:
        requested_username = username
        normalized_username = normalize_username(username)
        if not normalized_username:
            return ProfileOpenResult(
                requested_username=requested_username,
                normalized_username="",
                final_url=getattr(page, "url", ""),
                matched_username=None,
                status=ProfileOpenStatus.INVALID_USERNAME,
                success=False,
                error="Invalid Instagram username",
            )

        profile_url = build_profile_url(normalized_username)
        try:
            await self.retryable_goto(
                page,
                profile_url,
                wait_until="domcontentloaded",
                timeout=self.config.browser.timeout_ms,
            )
        except Exception as exc:
            return ProfileOpenResult(
                requested_username=requested_username,
                normalized_username=normalized_username,
                final_url=getattr(page, "url", ""),
                matched_username=None,
                status=ProfileOpenStatus.NAVIGATION_ERROR,
                success=False,
                error=f"Error loading profile after retries: {exc}",
            )

        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

        final_url = getattr(page, "url", "")
        if is_auth_lost_url(final_url):
            return _failure_result(
                requested_username=requested_username,
                normalized_username=normalized_username,
                final_url=final_url,
                status=ProfileOpenStatus.AUTH_LOST,
                error="Instagram session redirected to login",
            )
        if is_challenge_url(final_url):
            return _failure_result(
                requested_username=requested_username,
                normalized_username=normalized_username,
                final_url=final_url,
                status=ProfileOpenStatus.CHALLENGE,
                error="Instagram challenge or 2FA required",
            )
        if await profile_not_found(page):
            return _failure_result(
                requested_username=requested_username,
                normalized_username=normalized_username,
                final_url=final_url,
                status=ProfileOpenStatus.NOT_FOUND,
                error="Instagram username does not exist",
            )

        matched_usernames = await self.detect_profile_usernames(page)
        mismatched_username = next(
            (
                candidate
                for candidate in matched_usernames
                if candidate != normalized_username
            ),
            None,
        )
        if (
            mismatched_username is not None
            or normalized_username not in matched_usernames
        ):
            matched_username = mismatched_username or (
                matched_usernames[0] if matched_usernames else None
            )
            return ProfileOpenResult(
                requested_username=requested_username,
                normalized_username=normalized_username,
                final_url=final_url,
                matched_username=matched_username,
                status=ProfileOpenStatus.WRONG_PROFILE,
                success=False,
                error=(
                    "Instagram profile identity mismatch "
                    f"(expected={normalized_username}, matched={matched_username})"
                ),
            )

        return ProfileOpenResult(
            requested_username=requested_username,
            normalized_username=normalized_username,
            final_url=final_url,
            matched_username=normalized_username,
            status=ProfileOpenStatus.SUCCESS,
            success=True,
            error=None,
        )

    async def detect_profile_usernames(self, page: Page) -> list[str]:
        candidates = (
            extract_username_from_profile_url(getattr(page, "url", "")),
            extract_username_from_profile_url(
                await _read_page_attribute(
                    page,
                    "link[rel='canonical']",
                    "href",
                )
            ),
            extract_username_from_profile_url(
                await _read_page_attribute(
                    page,
                    "meta[property='og:url']",
                    "content",
                )
            ),
        )
        usernames: list[str] = []
        for candidate in candidates:
            if candidate and candidate not in usernames:
                usernames.append(candidate)
        return usernames


def normalize_username(username: str) -> str:
    normalized = username.strip().strip("/").lstrip("@").strip().lower()
    return normalized.strip("/")


def build_profile_url(normalized_username: str) -> str:
    return f"{_INSTAGRAM_BASE_URL}/{normalized_username}/"


def is_auth_lost_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return "/accounts/login" in path or path.rstrip("/") == "/login"


def is_challenge_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return "/challenge" in path or "/two_factor" in path


def extract_username_from_profile_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        return None
    first = path_parts[0].strip().lower()
    if first in {"accounts", "challenge", "explore", "p", "reel", "stories"}:
        return None
    return first or None


async def profile_not_found(page: Page, timeout_ms: int = 1500) -> bool:
    main = page.locator("main")
    hit = main.get_by_text(_UNAVAILABLE_RE).first

    try:
        await hit.wait_for(state="visible", timeout=timeout_ms)
        return True
    except PlaywrightTimeoutError:
        pass
    except Exception:
        pass

    try:
        main_text = await main.inner_text(timeout=timeout_ms)
        return bool(_UNAVAILABLE_RE.search(main_text))
    except Exception:
        return False


async def _read_page_attribute(
    page: Page,
    selector: str,
    attribute_name: str,
) -> str | None:
    try:
        value = await page.locator(selector).first.get_attribute(
            attribute_name,
            timeout=1000,
        )
    except Exception:
        return None
    return value if isinstance(value, str) and value else None


def _failure_result(
    *,
    requested_username: str,
    normalized_username: str,
    final_url: str,
    status: ProfileOpenStatus,
    error: str,
) -> ProfileOpenResult:
    return ProfileOpenResult(
        requested_username=requested_username,
        normalized_username=normalized_username,
        final_url=final_url,
        matched_username=None,
        status=status,
        success=False,
        error=error,
    )


__all__ = [
    "InstagramProfileNavigator",
    "build_profile_url",
    "extract_username_from_profile_url",
    "is_auth_lost_url",
    "is_challenge_url",
    "normalize_username",
    "profile_not_found",
]
