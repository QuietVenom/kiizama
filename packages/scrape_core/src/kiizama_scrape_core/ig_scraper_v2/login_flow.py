from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from playwright.async_api import Locator, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .interactions import Sleeper, human_delay, human_type
from .logging_utils import sanitize_log_value

RetryableGoto = Callable[..., Awaitable[Any]]


@dataclass(slots=True)
class LoginFlowResult:
    success: bool
    status: str
    message: str
    error: str | None = None


@dataclass(slots=True)
class LoginPageNavigationResult:
    error: LoginFlowResult | None = None
    domcontentloaded_at: float | None = None


@dataclass(slots=True)
class LoginAttemptResult:
    success: bool
    failure_reason: str | None = None


USERNAME_FIELD_SELECTOR = ", ".join(
    [
        "input[name='username']",
        "input[aria-label*='Username']",
        "input[aria-label*='Email']",
        "input[aria-label*='Mobile']",
        "input[type='email']",
        "input[name='email']",
    ]
)
PASSWORD_FIELD_SELECTOR = ", ".join(
    [
        "input[name='password']",
        "input[aria-label*='Password']",
        "input[type='password']",
    ]
)


class InstagramLoginFlow:
    """Reusable Playwright login routine for Instagram v2 flows."""

    def __init__(
        self,
        *,
        timeout_ms: int,
        retryable_goto: RetryableGoto,
        logger: logging.Logger | None = None,
        sleeper: Sleeper = asyncio.sleep,
        rng: random.Random | None = None,
    ) -> None:
        self.timeout_ms = timeout_ms
        self.retryable_goto = retryable_goto
        self.logger = logger or logging.getLogger(
            "kiizama_scrape_core.ig_scraper_v2.login_flow"
        )
        self.sleeper = sleeper
        self.rng = rng

    async def execute(
        self,
        page: Page,
        *,
        login_username: str,
        password: str,
    ) -> LoginFlowResult:
        normalized_username = login_username.strip()
        if not normalized_username or not password:
            self.logger.error("Missing Instagram login credentials")
            return LoginFlowResult(
                success=False,
                status="error",
                message="Missing Instagram login credentials",
                error="Missing Instagram login credentials",
            )

        navigation_result = await self._navigate_to_login_page(page)
        if navigation_result.error is not None:
            return navigation_result.error

        login_attempt = await self._perform_login(
            page,
            login_username=normalized_username,
            password=password,
            domcontentloaded_at=navigation_result.domcontentloaded_at,
        )
        if not login_attempt.success:
            failure_reason = login_attempt.failure_reason or "Login failed"
            return LoginFlowResult(
                success=False,
                status="error",
                message=f"Login failed: {failure_reason}",
                error=failure_reason,
            )

        if self.requires_challenge(page):
            return LoginFlowResult(
                success=False,
                status="challenge",
                message="Checkpoint or 2FA required",
                error="Checkpoint or 2FA required",
            )

        return LoginFlowResult(success=True, status="ok", message="Login successful")

    async def _navigate_to_login_page(self, page: Page) -> LoginPageNavigationResult:
        # TODO: Move login timing instrumentation behind a diagnostic flag or
        # downgrade it to DEBUG before enabling ig_scraper_v2 in worker/prod.
        start = time.perf_counter()
        self.logger.info(
            "Navigating to Instagram login page "
            "(wait_until=domcontentloaded, timeout_ms=%s)",
            self.timeout_ms,
        )
        try:
            await self.retryable_goto(
                page,
                "https://www.instagram.com/accounts/login/",
                wait_until="domcontentloaded",
                timeout=self.timeout_ms,
            )
        except Exception as exc:  # pragma: no cover - network variances
            sanitized_error = sanitize_log_value(exc)
            self.logger.error(
                "Error navigating to login page after retries: %s",
                sanitized_error,
            )
            return LoginPageNavigationResult(
                error=LoginFlowResult(
                    success=False,
                    status="error",
                    message="Error navigating to login page",
                    error=f"Error navigating to login page: {sanitized_error}",
                )
            )
        navigation_returned_at = time.perf_counter()
        self.logger.info(
            "Instagram login page navigation returned "
            "(wait_until=domcontentloaded, elapsed_ms=%s)",
            _elapsed_ms(start),
        )

        start = time.perf_counter()
        self.logger.info(
            "Waiting for Instagram login page load state "
            "(state=domcontentloaded, timeout_ms=%s)",
            self.timeout_ms,
        )
        try:
            await page.wait_for_load_state(
                "domcontentloaded",
                timeout=self.timeout_ms,
            )
        except PlaywrightTimeoutError:
            self.logger.warning(
                "Instagram login page did not reach domcontentloaded (elapsed_ms=%s)",
                _elapsed_ms(start),
            )
            domcontentloaded_at = navigation_returned_at
        else:
            domcontentloaded_at = time.perf_counter()
            self.logger.info(
                "Instagram login page reached domcontentloaded (elapsed_ms=%s)",
                _elapsed_ms(start),
            )

        return LoginPageNavigationResult(domcontentloaded_at=domcontentloaded_at)

    async def _perform_login(
        self,
        page: Page,
        *,
        login_username: str,
        password: str,
        domcontentloaded_at: float | None,
    ) -> LoginAttemptResult:
        username_locator = await self._wait_for_visible_css_locator(
            page,
            USERNAME_FIELD_SELECTOR,
        )
        password_locator = await self._wait_for_visible_css_locator(
            page,
            PASSWORD_FIELD_SELECTOR,
        )

        if username_locator is None or password_locator is None:
            missing_fields = [
                label
                for label, locator in (
                    ("username field", username_locator),
                    ("password field", password_locator),
                )
                if locator is None
            ]
            failure_reason = f"Login fields not found: {', '.join(missing_fields)}"
            self.logger.error(failure_reason)
            return LoginAttemptResult(success=False, failure_reason=failure_reason)

        await username_locator.click(timeout=1500)
        await username_locator.fill("")
        self.logger.info(
            "Starting Instagram credential typing "
            "(elapsed_since_domcontentloaded_ms=%s)",
            _elapsed_ms(domcontentloaded_at)
            if domcontentloaded_at is not None
            else "unknown",
        )
        await human_type(
            username_locator,
            login_username,
            sleeper=self.sleeper,
            rng=self.rng,
        )
        await human_delay(400, 700, sleeper=self.sleeper, rng=self.rng)
        await password_locator.click(timeout=1500)
        await password_locator.fill("")
        await human_type(
            password_locator,
            password,
            sleeper=self.sleeper,
            rng=self.rng,
        )
        await human_delay(400, 700, sleeper=self.sleeper, rng=self.rng)

        login_button = await self._find_login_button(page)
        if login_button is None:
            failure_reason = "Login button not found or disabled"
            self.logger.error(failure_reason)
            return LoginAttemptResult(success=False, failure_reason=failure_reason)

        await login_button.click(timeout=1500)

        # TODO: Expand post-login classification before worker integration:
        # wrong password, checkpoint, save-login prompt, suspicious-login prompt,
        # and other non-2FA interstitials should have distinct failure reasons.
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=self.timeout_ms)
        except Exception:
            self.logger.debug("Login navigation did not reach domcontentloaded")

        await human_delay(500, 1000, sleeper=self.sleeper, rng=self.rng)

        for attempt in range(3):
            await self.sleeper(1.5)
            current_url = page.url
            self.logger.debug(
                "Post-login check attempt %s (%s)",
                attempt + 1,
                current_url,
            )
            if "/accounts/login" not in current_url and "/login" not in current_url:
                self.logger.debug("Post-login redirect detected")
                return LoginAttemptResult(success=True)

        failure_reason = (
            "No post-login redirect detected after submit "
            f"(final_url={_sanitize_url_for_log(page.url)})"
        )
        self.logger.error(failure_reason)
        return LoginAttemptResult(success=False, failure_reason=failure_reason)

    @staticmethod
    async def _wait_for_visible_css_locator(
        page: Page,
        selector: str,
    ) -> Locator | None:
        # TODO: Put selector lookup elapsed_ms behind the same diagnostic flag
        # if login field detection becomes slow again with real Instagram pages.
        locator = page.locator(selector).first
        try:
            await locator.wait_for(state="visible", timeout=5000)
        except Exception:
            return None
        return locator

    @staticmethod
    async def _find_login_button(page: Page) -> Locator | None:
        login_button_candidates: list[Callable[[Page], Locator]] = [
            lambda p: p.get_by_role(
                "button",
                name=re.compile(r"^iniciar sesión$", re.I),
            ),
            lambda p: p.get_by_role(
                "button",
                name=re.compile(r"iniciar sesión", re.I),
            ),
            lambda p: p.get_by_role(
                "button",
                name=re.compile(r"^log in$", re.I),
            ),
            lambda p: p.get_by_role(
                "button",
                name=re.compile(r"log in", re.I),
            ),
            lambda p: p.locator("button[type='submit']").first,
        ]

        for get_candidate in login_button_candidates:
            try:
                candidate = get_candidate(page).first
                await candidate.wait_for(state="visible", timeout=1000)
                aria_disabled = await candidate.get_attribute("aria-disabled")
                is_disabled = await candidate.is_disabled()
                if aria_disabled == "true" or is_disabled:
                    continue
                return candidate
            except PlaywrightTimeoutError:
                continue
            except Exception:
                continue
        return None

    @staticmethod
    def requires_challenge(page: Page) -> bool:
        current_url = page.url
        return "/challenge" in current_url or "/two_factor" in current_url


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _sanitize_url_for_log(url: str) -> str:
    return url.split("?", 1)[0]


__all__ = ["InstagramLoginFlow", "LoginFlowResult", "RetryableGoto"]
