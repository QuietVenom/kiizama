from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from dataclasses import dataclass

from playwright.async_api import Locator, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .base import BaseInstagramWorker


@dataclass(slots=True)
class LoginFlowResult:
    success: bool
    status: str
    message: str
    error: str | None = None


class InstagramLoginFlow:
    """Reusable Playwright login routine for Instagram flows."""

    def __init__(
        self,
        worker: BaseInstagramWorker,
        *,
        login_username: str,
        password: str,
    ) -> None:
        self.worker = worker
        self.login_username = login_username.strip()
        self.password = password
        self.logger = worker.logger
        self.timeout_ms = worker.timeout_ms

    async def execute(self, page: Page) -> LoginFlowResult:
        if not self.login_username or not self.password:
            self.logger.error("Missing Instagram login credentials")
            return LoginFlowResult(
                success=False,
                status="error",
                message="Missing Instagram login credentials",
                error="Missing Instagram login credentials",
            )

        navigation_result = await self._navigate_to_login_page(page)
        if navigation_result is not None:
            return navigation_result

        login_success = await self._perform_login(page)
        if not login_success:
            return LoginFlowResult(
                success=False,
                status="error",
                message="Login failed",
                error="Login failed",
            )

        if self._requires_challenge(page):
            return LoginFlowResult(
                success=False,
                status="challenge",
                message="Checkpoint or 2FA required",
                error="Checkpoint or 2FA required",
            )

        return LoginFlowResult(success=True, status="ok", message="Login successful")

    async def _navigate_to_login_page(self, page: Page) -> LoginFlowResult | None:
        try:
            await self.worker.retryable_goto(
                page,
                "https://www.instagram.com/accounts/login/",
                wait_until="domcontentloaded",
                timeout=self.timeout_ms,
            )

        except Exception as exc:  # pragma: no cover - network variances
            self.logger.error("Error navigating to login page after retries: %s", exc)
            return LoginFlowResult(
                success=False,
                status="error",
                message="Error navigating to login page",
                error=f"Error navigating to login page: {exc}",
            )

        try:
            await page.wait_for_load_state("domcontentloaded")
        except asyncio.TimeoutError:
            self.logger.warning("Login page did not reach stable state in time")

        return None

    async def _perform_login(self, page: Page) -> bool:
        username_selectors = [
            "input[name='username']",
            "input[aria-label*='Username']",
            "input[aria-label*='Email']",
            "input[aria-label*='Mobile']",
            "input[type='email']",
            "input[name='email']",
        ]
        password_selectors = [
            "input[name='password']",
            "input[aria-label*='Password']",
            "input[type='password']",
        ]

        username_locator = None
        password_locator = None

        for selector in username_selectors:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                username_locator = page.locator(selector).first
                break
            except Exception:
                continue

        for selector in password_selectors:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                password_locator = page.locator(selector).first
                break
            except Exception:
                continue

        if username_locator is None or password_locator is None:
            self.logger.error("Login fields not found")
            return False

        await username_locator.click(timeout=1500)
        await username_locator.fill("")
        await self.worker.human_type(username_locator, self.login_username)
        await self.worker.human_delay(400, 700)
        await password_locator.click(timeout=1500)
        await password_locator.fill("")
        await self.worker.human_type(password_locator, self.password)
        await self.worker.human_delay(400, 700)

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
        login_button = None

        for get_candidate in login_button_candidates:
            try:
                candidate = get_candidate(page).first
                await candidate.wait_for(state="visible", timeout=1000)

                aria_disabled = await candidate.get_attribute("aria-disabled")
                is_disabled = await candidate.is_disabled()
                if aria_disabled == "true" or is_disabled:
                    continue

                login_button = candidate
                break
            except PlaywrightTimeoutError:
                continue
            except Exception:
                continue

        if login_button is None:
            self.logger.error("Login button not found (or disabled)")
            return False

        await login_button.click(timeout=1500)

        try:
            await page.wait_for_load_state("domcontentloaded", timeout=self.timeout_ms)
        except Exception:
            self.logger.debug("Login navigation did not reach network idle")

        await self.worker.human_delay(500, 1000)

        for attempt in range(3):
            await asyncio.sleep(1.5)
            current_url = page.url
            self.logger.debug(
                "Post-login check attempt %s (%s)",
                attempt + 1,
                current_url,
            )
            if "/accounts/login" not in current_url and "/login" not in current_url:
                self.logger.debug("Post-login redirect detected")
                return True

        self.logger.debug(
            "No post-login redirect after retries, final URL %s", page.url
        )
        return False

    @staticmethod
    def _requires_challenge(page: Page) -> bool:
        current_url = page.url
        return "/challenge" in current_url or "/two_factor" in current_url


__all__ = ["InstagramLoginFlow", "LoginFlowResult"]
