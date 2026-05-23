from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .browser import InstagramBrowserSession
from .classes import SessionValidationResult
from .config import ScraperV2Config
from .interactions import Sleeper
from .models import ProfileOpenResult, ProfileOpenStatus
from .pacing import sleep_for_next_delay
from .ports import InstagramCredentialsStore
from .profile_navigation import InstagramProfileNavigator, normalize_username
from .session import InstagramSessionBootstrapper
from .session_context import build_effective_session_context
from .stealth import add_stealth

BrowserSessionFactory = Callable[..., Any]
NavigatorFactory = Callable[..., Any]
SessionBootstrapperFactory = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class ProfileOpenRunResult:
    success: bool
    credential_id: str | None
    session_message: str
    results: dict[str, ProfileOpenResult] = field(default_factory=dict)
    error: str | None = None


class InstagramProfileOpenRunner:
    def __init__(
        self,
        *,
        config: ScraperV2Config,
        credentials_store: InstagramCredentialsStore,
        usernames: list[str],
        logger: logging.Logger | None = None,
        sleeper: Sleeper = asyncio.sleep,
        rng: random.Random | None = None,
        session_bootstrapper_factory: SessionBootstrapperFactory | None = None,
        browser_session_factory: BrowserSessionFactory | None = None,
        navigator_factory: NavigatorFactory | None = None,
    ) -> None:
        self.config = config
        self.credentials_store = credentials_store
        self.usernames = usernames
        self.logger = logger or logging.getLogger(
            "kiizama_scrape_core.ig_scraper_v2.runner"
        )
        self.sleeper = sleeper
        self.rng = rng or random.Random()
        self.session_bootstrapper_factory = session_bootstrapper_factory
        self.browser_session_factory = browser_session_factory
        self.navigator_factory = navigator_factory

    async def run(self) -> ProfileOpenRunResult:
        session_result = await self._ensure_session()
        if not session_result.success:
            return self._session_failure_result(session_result)

        effective_context = build_effective_session_context(
            self.config,
            session_result.storage_state,
        )
        browser_session = self._create_browser_session(
            config=effective_context.config,
            storage_state=effective_context.storage_state,
            extra_http_headers=effective_context.extra_http_headers,
            credential_id=session_result.credential_id,
        )

        results: dict[str, ProfileOpenResult] = {}
        async with browser_session as browser:
            context = browser.context
            if context is None:
                error = "Playwright browser context could not be initialized"
                return ProfileOpenRunResult(
                    success=False,
                    credential_id=session_result.credential_id,
                    session_message=session_result.message,
                    results=self._failure_results(error),
                    error=error,
                )

            navigator = self._create_navigator(
                config=effective_context.config,
                retryable_goto=browser.retryable_goto,
            )
            total = len(self.usernames)
            for index, username in enumerate(self.usernames):
                page = await context.new_page()
                try:
                    await add_stealth(
                        page,
                        locale=effective_context.config.browser.locale,
                        logger=self.logger,
                    )
                    result = await navigator.open_profile(page, username)
                finally:
                    await page.close()
                results[username] = result
                if index + 1 < total:
                    await sleep_for_next_delay(
                        self.config.pacing,
                        sleeper=self.sleeper,
                        rng=self.rng,
                    )

        return ProfileOpenRunResult(
            success=all(result.success for result in results.values()),
            credential_id=session_result.credential_id,
            session_message=session_result.message,
            results=results,
            error=None,
        )

    async def _ensure_session(self) -> SessionValidationResult:
        if self.session_bootstrapper_factory is not None:
            bootstrapper = self.session_bootstrapper_factory(
                config=self.config,
                credentials_store=self.credentials_store,
                logger=self.logger,
                sleeper=self.sleeper,
                rng=self.rng,
            )
        else:
            bootstrapper = InstagramSessionBootstrapper(
                config=self.config,
                credentials_store=self.credentials_store,
                logger=self.logger,
                sleeper=self.sleeper,
                rng=self.rng,
            )
        return await bootstrapper.ensure_session()

    def _create_browser_session(
        self,
        **kwargs: Any,
    ) -> Any:
        if self.browser_session_factory is not None:
            return self.browser_session_factory(
                logger=self.logger,
                sleeper=self.sleeper,
                rng=self.rng,
                **kwargs,
            )
        return InstagramBrowserSession(
            logger=self.logger,
            sleeper=self.sleeper,
            rng=self.rng,
            **kwargs,
        )

    def _create_navigator(self, **kwargs: Any) -> Any:
        if self.navigator_factory is not None:
            return self.navigator_factory(logger=self.logger, **kwargs)
        return InstagramProfileNavigator(logger=self.logger, **kwargs)

    def _session_failure_result(
        self,
        session_result: SessionValidationResult,
    ) -> ProfileOpenRunResult:
        error = session_result.error or session_result.message
        return ProfileOpenRunResult(
            success=False,
            credential_id=session_result.credential_id,
            session_message=session_result.message,
            results=self._failure_results(error),
            error=error,
        )

    def _failure_results(self, error: str) -> dict[str, ProfileOpenResult]:
        return {
            username: ProfileOpenResult(
                requested_username=username,
                normalized_username=normalize_username(username),
                final_url="",
                matched_username=None,
                status=ProfileOpenStatus.NAVIGATION_ERROR,
                success=False,
                error=error,
            )
            for username in self.usernames
        }


__all__ = [
    "InstagramProfileOpenRunner",
    "ProfileOpenRunResult",
]
