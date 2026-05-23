from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Callable
from typing import Any

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .browser import InstagramBrowserSession, PlaywrightBrowserNotInstalledError
from .classes import (
    CredentialCandidate,
    SessionValidationResult,
)
from .config import ScraperV2Config
from .interactions import Sleeper
from .logging_utils import (
    redacted_identifier,
    redacted_login_username,
    sanitize_exception_for_log,
    sanitize_log_value,
)
from .login_flow import InstagramLoginFlow
from .ports import InstagramCredentialsStore
from .session_context import build_effective_session_context

BrowserSessionFactory = Callable[..., Any]
LoginFlowFactory = Callable[..., Any]

MAX_LOGIN_ATTEMPTS = 3
MAX_CREDENTIALS_FETCH = 200


class InstagramSessionBootstrapper:
    """Validate or refresh an Instagram session for scraper v2."""

    def __init__(
        self,
        *,
        config: ScraperV2Config,
        credentials_store: InstagramCredentialsStore,
        logger: logging.Logger | None = None,
        sleeper: Sleeper = asyncio.sleep,
        rng: random.Random | None = None,
        browser_session_factory: BrowserSessionFactory | None = None,
        login_flow_factory: LoginFlowFactory | None = None,
    ) -> None:
        self.config = config
        self.credentials_store = credentials_store
        self.logger = logger or logging.getLogger(
            "kiizama_scrape_core.ig_scraper_v2.session"
        )
        self.sleeper = sleeper
        self.rng = rng or random.Random()
        self.browser_session_factory = browser_session_factory
        self.login_flow_factory = login_flow_factory

    async def ensure_session(self) -> SessionValidationResult:
        credentials = await self.credentials_store.list_credentials(
            limit=MAX_CREDENTIALS_FETCH
        )
        viable = [
            credential
            for credential in credentials
            if credential.has_session() or credential.has_login()
        ]

        if not viable:
            message = "No Instagram credentials available"
            self.logger.error(message)
            return SessionValidationResult(
                success=False,
                credential_id=None,
                storage_state=None,
                message=message,
                error=message,
            )

        self.rng.shuffle(viable)
        # TODO: Add DEBUG-only credential order observability after shuffle
        # before worker integration. Include id, has_session, and has_login only.
        max_attempts = min(MAX_LOGIN_ATTEMPTS, len(viable))
        failed_ids: list[str] = []

        for idx, credential in enumerate(viable[:max_attempts], start=1):
            self.logger.info(
                "Instagram credential attempt %s/%s using id=%s username=%s",
                idx,
                max_attempts,
                redacted_identifier(credential.id),
                redacted_login_username(credential.login_username),
            )
            try:
                result = await self._ensure_session_for_credential(credential)
            except PlaywrightBrowserNotInstalledError as exc:
                message = str(exc)
                self.logger.error(message)
                return SessionValidationResult(
                    success=False,
                    credential_id=credential.id,
                    storage_state=None,
                    message=message,
                    error=message,
                )
            except Exception as exc:
                sanitized_error = sanitize_exception_for_log(exc)
                message = (
                    f"Unexpected Instagram session validation error: {sanitized_error}"
                )
                self.logger.exception(
                    "Unexpected session validation error for credential id=%s",
                    redacted_identifier(credential.id),
                )
                result = SessionValidationResult(
                    success=False,
                    credential_id=credential.id,
                    storage_state=credential.session,
                    message=message,
                    error=message,
                )

            if result.success:
                self.logger.info(
                    "Instagram session ready for id=%s username=%s",
                    redacted_identifier(credential.id),
                    redacted_login_username(credential.login_username),
                )
                return result

            failed_ids.append(credential.id)
            self.logger.warning(
                "Instagram credential attempt failed for id=%s username=%s: %s",
                redacted_identifier(credential.id),
                redacted_login_username(credential.login_username),
                sanitize_log_value(result.error or result.message),
            )

        if failed_ids:
            self.logger.error(
                "Instagram credential attempts failed after %s tries. Failed ids=%s",
                len(failed_ids),
                ", ".join(
                    redacted_identifier(credential_id) for credential_id in failed_ids
                ),
            )

        message = "Instagram login failed for all attempted credentials"
        return SessionValidationResult(
            success=False,
            credential_id=None,
            storage_state=None,
            message=message,
            error=message,
        )

    async def _ensure_session_for_credential(
        self,
        credential: CredentialCandidate,
    ) -> SessionValidationResult:
        effective_context = build_effective_session_context(
            self.config,
            credential.session,
        )

        browser_session = self._create_browser_session(
            effective_context.config,
            storage_state=effective_context.storage_state,
            extra_http_headers=effective_context.extra_http_headers,
            credential_id=credential.id,
        )

        async with browser_session as browser:
            page = browser.page
            if page is None:
                message = "Playwright page could not be initialized"
                return SessionValidationResult(
                    success=False,
                    credential_id=credential.id,
                    storage_state=effective_context.storage_state,
                    message=message,
                    error=message,
                )

            if credential.has_session():
                self.logger.info(
                    "Validating stored session for credential id=%s",
                    redacted_identifier(credential.id),
                )
                if await self._navigate_to_home(
                    browser,
                    page,
                ) and await self._has_logged_in_markers(page):
                    persisted = await self._persist_storage_state(
                        browser,
                        credential.id,
                        fallback_state=effective_context.storage_state,
                    )
                    return SessionValidationResult(
                        success=True,
                        credential_id=credential.id,
                        storage_state=persisted or effective_context.storage_state,
                        message="Existing Instagram session is valid",
                    )

                self.logger.info(
                    "Stored session invalid for credential id=%s",
                    redacted_identifier(credential.id),
                )

            login_username, password = self._load_login_credentials(credential)
            if not login_username or not password:
                message = "Missing Instagram login credentials"
                return SessionValidationResult(
                    success=False,
                    credential_id=credential.id,
                    storage_state=effective_context.storage_state,
                    message=message,
                    error=message,
                )

            login_flow = self._create_login_flow(browser)
            login_result = await login_flow.execute(
                page,
                login_username=login_username,
                password=password,
            )
            if not login_result.success:
                return SessionValidationResult(
                    success=False,
                    credential_id=credential.id,
                    storage_state=effective_context.storage_state,
                    message=login_result.message,
                    error=login_result.error or login_result.message,
                )

            await self._navigate_to_home(browser, page)
            if not await self._has_logged_in_markers(page):
                message = "Unable to confirm authenticated session after login"
                return SessionValidationResult(
                    success=False,
                    credential_id=credential.id,
                    storage_state=effective_context.storage_state,
                    message=message,
                    error=message,
                )

            persisted = await self._persist_storage_state(
                browser,
                credential.id,
                fallback_state=effective_context.storage_state,
            )
            return SessionValidationResult(
                success=True,
                credential_id=credential.id,
                storage_state=persisted or effective_context.storage_state,
                message="Instagram session refreshed via login",
            )

    def _create_browser_session(
        self,
        config: ScraperV2Config,
        *,
        storage_state: dict[str, Any] | None,
        extra_http_headers: dict[str, str],
        credential_id: str,
    ) -> Any:
        if self.browser_session_factory is not None:
            return self.browser_session_factory(
                config=config,
                storage_state=storage_state,
                extra_http_headers=extra_http_headers,
                credential_id=credential_id,
                logger=self.logger,
                sleeper=self.sleeper,
                rng=self.rng,
            )
        return InstagramBrowserSession(
            config=config,
            storage_state=storage_state,
            extra_http_headers=extra_http_headers,
            credential_id=credential_id,
            logger=self.logger,
            sleeper=self.sleeper,
            rng=self.rng,
        )

    def _create_login_flow(self, browser: Any) -> Any:
        kwargs = {
            "timeout_ms": self.config.browser.timeout_ms,
            "retryable_goto": browser.retryable_goto,
            "logger": self.logger,
            "sleeper": self.sleeper,
            "rng": self.rng,
        }
        if self.login_flow_factory is not None:
            return self.login_flow_factory(**kwargs)
        return InstagramLoginFlow(**kwargs)

    def _load_login_credentials(
        self,
        credential: CredentialCandidate,
    ) -> tuple[str | None, str | None]:
        login_username = (credential.login_username or "").strip()
        if not login_username or not credential.encrypted_password:
            self.logger.warning(
                "Credential id=%s missing login_username or password",
                redacted_identifier(credential.id),
            )
            return None, None

        try:
            password = self.credentials_store.decrypt_password(
                credential.encrypted_password
            )
        except Exception as exc:
            self.logger.error(
                "Failed to decrypt Instagram password for id=%s: %s",
                redacted_identifier(credential.id),
                sanitize_log_value(exc),
            )
            return None, None

        return login_username, password

    async def _persist_storage_state(
        self,
        browser: Any,
        credential_id: str,
        *,
        fallback_state: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if browser.context is None:
            return fallback_state

        try:
            state = dict(await browser.context.storage_state())
        except Exception as exc:  # pragma: no cover - IO variability
            self.logger.warning(
                "Failed to capture storage state: %s", sanitize_log_value(exc)
            )
            return fallback_state

        try:
            persisted = await self.credentials_store.persist_session(
                credential_id,
                state,
            )
        except Exception as exc:  # pragma: no cover - persistence variability
            self.logger.error(
                "Failed to persist Instagram session for id=%s: %s",
                redacted_identifier(credential_id),
                sanitize_log_value(exc),
            )
            return state

        if not persisted:
            self.logger.warning(
                "Instagram session persistence returned false for id=%s",
                redacted_identifier(credential_id),
            )
        return state

    async def _navigate_to_home(self, browser: Any, page: Page) -> bool:
        try:
            await browser.retryable_goto(
                page,
                "https://www.instagram.com/",
                wait_until="domcontentloaded",
                timeout=self.config.browser.timeout_ms,
            )
        except Exception as exc:
            self.logger.error(
                "Failed to navigate to Instagram home: %s",
                sanitize_log_value(exc),
            )
            return False

        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

        return True

    async def _has_logged_in_markers(self, page: Page) -> bool:
        try:
            self.logger.info("Checking logged-in markers")

            story_tray = page.locator("div[data-pagelet='story_tray']")
            if await story_tray.first.is_visible(timeout=1500):
                self.logger.info("Story tray marker present")
            else:
                self.logger.info("Story tray marker not visible")

            candidates = [
                page.get_by_role("button", name="Settings"),
                page.get_by_role("button", name="Configuración"),
                page.locator("[aria-label='Settings']"),
                page.locator("[aria-label='Configuración']"),
                page.locator(
                    "a[aria-label*='Settings'], button[aria-label*='Settings']"
                ),
            ]

            for candidate in candidates:
                if await candidate.first.is_visible(timeout=1500):
                    self.logger.info(
                        "Settings/menu marker present: %s",
                        await candidate.first.get_attribute("aria-label"),
                    )
                    return True

            return await story_tray.first.is_visible(timeout=250)

        except PlaywrightTimeoutError:
            self.logger.info("Timeout while checking logged-in markers")
            return False
        except Exception as exc:
            self.logger.debug(
                "Error checking login markers: %s", sanitize_log_value(exc)
            )
            return False


__all__ = [
    "InstagramSessionBootstrapper",
    "MAX_CREDENTIALS_FETCH",
    "MAX_LOGIN_ATTEMPTS",
]
