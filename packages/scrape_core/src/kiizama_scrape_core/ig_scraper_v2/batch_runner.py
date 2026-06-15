from __future__ import annotations

import asyncio
import logging
import random
from collections import deque
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from .browser import InstagramBrowserSession
from .classes import (
    InstagramScrapeResult,
    SessionValidationResult,
)
from .config import ScraperV2Config
from .interactions import Sleeper
from .logging_utils import (
    format_counters,
    proxy_mode_label,
    redacted_identifier,
    sanitize_log_value,
)
from .metrics import calculate_metrics_from_scrape
from .models import BatchScrapeCounters, InstagramBatchScrapeRunResult
from .pacing import sleep_for_next_delay
from .ports import InstagramCredentialsStore
from .profile_navigation import InstagramProfileNavigator, normalize_username
from .profile_scraper import InstagramProfileScraper
from .schemas import InstagramBatchScrapeResponse
from .session import InstagramSessionBootstrapper
from .session_context import build_effective_session_context
from .stealth import add_stealth

BrowserSessionFactory = Callable[..., Any]
NavigatorFactory = Callable[..., Any]
ProfileScraperFactory = Callable[..., Any]
SessionBootstrapperFactory = Callable[..., Any]


class InstagramBatchScrapeRunner:
    """Run v2 snapshot scraping in memory with controlled concurrency."""

    def __init__(
        self,
        *,
        config: ScraperV2Config,
        credentials_store: InstagramCredentialsStore,
        usernames: list[str],
        max_posts: int = 12,
        logger: logging.Logger | None = None,
        sleeper: Sleeper = asyncio.sleep,
        rng: random.Random | None = None,
        session_bootstrapper_factory: SessionBootstrapperFactory | None = None,
        browser_session_factory: BrowserSessionFactory | None = None,
        navigator_factory: NavigatorFactory | None = None,
        profile_scraper_factory: ProfileScraperFactory | None = None,
        job_id: str | None = None,
    ) -> None:
        self.config = config
        self.credentials_store = credentials_store
        self.usernames = normalize_usernames(usernames)
        self.max_posts = max_posts
        self.logger = logger or logging.getLogger(
            "kiizama_scrape_core.ig_scraper_v2.batch_runner"
        )
        self.sleeper = sleeper
        self.rng = rng or random.Random()
        self.session_bootstrapper_factory = session_bootstrapper_factory
        self.browser_session_factory = browser_session_factory
        self.navigator_factory = navigator_factory
        self.profile_scraper_factory = profile_scraper_factory
        self.job_id = job_id or "unknown"

        self.profile_queue: deque[str] = deque(self.usernames)
        self.results: dict[str, dict[str, Any]] = {}
        self.counters = BatchScrapeCounters(requested=len(self.usernames))

    async def run(self) -> InstagramBatchScrapeRunResult:
        if not self.usernames:
            result = InstagramBatchScrapeRunResult(
                success=False,
                credential_id=None,
                session_message="No usernames provided",
                results={},
                counters=self.counters,
                error="No usernames provided",
            )
            self._log_run_finished(result)
            return result

        session_result = await self._ensure_session()
        if not session_result.success:
            result = self._session_failure_result(session_result)
            self._log_run_finished(result)
            return result

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

        async with browser_session as browser:
            context = browser.context
            if context is None:
                error = "Playwright browser context could not be initialized"
                self._mark_all_failed(error)
                result = InstagramBatchScrapeRunResult(
                    success=False,
                    credential_id=session_result.credential_id,
                    session_message=session_result.message,
                    results=self.results,
                    counters=self.counters,
                    error=error,
                )
                self._log_run_finished(result)
                return result

            worker_count = min(
                self.config.crawler.max_concurrent,
                len(self.profile_queue),
            )
            workers = [
                asyncio.create_task(
                    self._profile_worker(
                        worker_name=f"worker-{index + 1}",
                        context=context,
                        retryable_goto=browser.retryable_goto,
                        scrape_config=effective_context.config,
                    )
                )
                for index in range(worker_count)
            ]
            await asyncio.gather(*workers)

        result = InstagramBatchScrapeRunResult(
            success=self.counters.failed == 0 and self.counters.not_found == 0,
            credential_id=session_result.credential_id,
            session_message=session_result.message,
            results=self.results,
            counters=self.counters,
            error=None,
        )
        self._log_run_finished(result)
        return result

    async def run_response(self) -> InstagramBatchScrapeResponse:
        from .adapter import to_instagram_batch_scrape_response

        return to_instagram_batch_scrape_response(await self.run())

    async def _profile_worker(
        self,
        *,
        worker_name: str,
        context: Any,
        retryable_goto: Callable[..., Any],
        scrape_config: ScraperV2Config,
    ) -> None:
        self.logger.info(
            "%s started, processing v2 scrape queue (job_id=%s)",
            worker_name,
            self.job_id,
        )
        while True:
            try:
                username = self.profile_queue.popleft()
            except IndexError:
                break

            self.logger.info(
                "%s scraping profile (job_id=%s, username=%s)",
                worker_name,
                self.job_id,
                username,
            )
            try:
                await self._scrape_single_profile(
                    username=username,
                    context=context,
                    retryable_goto=retryable_goto,
                    scrape_config=scrape_config,
                )
            except Exception as exc:
                self.logger.error(
                    "%s error scraping profile (job_id=%s, username=%s): %s",
                    worker_name,
                    self.job_id,
                    username,
                    sanitize_log_value(exc),
                )
                self._record_result(
                    username,
                    InstagramScrapeResult(
                        success=False,
                        error=f"Scraping error: {exc}",
                    ),
                )

            if self.profile_queue:
                await sleep_for_next_delay(
                    self.config.pacing,
                    sleeper=self.sleeper,
                    rng=self.rng,
                )
        self.logger.info(
            "%s finished, v2 scrape queue empty (job_id=%s)",
            worker_name,
            self.job_id,
        )

    async def _scrape_single_profile(
        self,
        *,
        username: str,
        context: Any,
        retryable_goto: Callable[..., Any],
        scrape_config: ScraperV2Config,
    ) -> None:
        page = await context.new_page()
        try:
            await add_stealth(
                page,
                locale=scrape_config.browser.locale,
                logger=self.logger,
            )
            navigator = self._create_navigator(
                config=scrape_config,
                retryable_goto=retryable_goto,
            )
            scraper = self._create_profile_scraper(
                config=scrape_config,
                navigator=navigator,
                max_posts=self.max_posts,
            )
            result = await scraper.scrape(page, username)
            if not result.success and not result.error:
                result.error = "Unable to scrape this profile"
            self._record_result(username, result)
        finally:
            await page.close()

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

    def _create_browser_session(self, **kwargs: Any) -> Any:
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

    def _create_profile_scraper(self, **kwargs: Any) -> Any:
        if self.profile_scraper_factory is not None:
            return self.profile_scraper_factory(
                logger=self.logger,
                sleeper=self.sleeper,
                rng=self.rng,
                **kwargs,
            )
        return InstagramProfileScraper(
            logger=self.logger,
            sleeper=self.sleeper,
            rng=self.rng,
            **kwargs,
        )

    def _session_failure_result(
        self,
        session_result: SessionValidationResult,
    ) -> InstagramBatchScrapeRunResult:
        error = session_result.error or session_result.message
        self._mark_all_failed(error)
        return InstagramBatchScrapeRunResult(
            success=False,
            credential_id=session_result.credential_id,
            session_message=session_result.message,
            results=self.results,
            counters=self.counters,
            error=error,
        )

    def _mark_all_failed(self, error: str) -> None:
        for username in self.usernames:
            if username in self.results:
                continue
            self.results[username] = _serialize_scrape_result(
                InstagramScrapeResult(success=False, error=error)
            )
            self.counters.failed += 1

    def _record_result(self, username: str, result: InstagramScrapeResult) -> None:
        self.results[username] = _serialize_scrape_result(result)
        if result.success:
            self.counters.successful += 1
            self.logger.info(
                "Scraped profile (job_id=%s, username=%s, status=success)",
                self.job_id,
                username,
            )
            return

        if result.error == "Instagram username does not exist":
            self.counters.not_found += 1
            self.logger.warning(
                "Profile scrape failed (job_id=%s, username=%s, status=not_found, error=%s)",
                self.job_id,
                username,
                sanitize_log_value(result.error),
            )
            return

        self.counters.failed += 1
        self.logger.error(
            "Profile scrape failed (job_id=%s, username=%s, status=%s, error=%s)",
            self.job_id,
            username,
            _profile_error_status(result.error),
            sanitize_log_value(result.error),
        )

    def _log_run_finished(self, result: InstagramBatchScrapeRunResult) -> None:
        self.logger.info(
            "IG v2 scrape run finished "
            "(job_id=%s, success=%s, credential_id=%s, proxy_mode=%s, counters=%s, error=%s)",
            self.job_id,
            str(result.success).lower(),
            redacted_identifier(result.credential_id),
            proxy_mode_label(self.config),
            format_counters(result.counters),
            sanitize_log_value(result.error) if result.error else "null",
        )


def normalize_usernames(usernames: list[str]) -> list[str]:
    normalized_usernames: list[str] = []
    seen: set[str] = set()
    for username in usernames:
        normalized = normalize_username(username)
        if not normalized or normalized in seen:
            continue
        normalized_usernames.append(normalized)
        seen.add(normalized)
    return normalized_usernames


def _serialize_scrape_result(result: InstagramScrapeResult) -> dict[str, Any]:
    result_dict = asdict(result)
    try:
        metrics = calculate_metrics_from_scrape(result_dict)
    except Exception:
        metrics = calculate_metrics_from_scrape({})
    metrics.pop("recommended_users", None)
    metrics.pop("user", None)
    result_dict["metrics"] = metrics
    return result_dict


def _profile_error_status(error: str | None) -> str:
    normalized = (error or "").lower()
    if "challenge" in normalized or "2fa" in normalized:
        return "challenge"
    if "redirected to login" in normalized or "auth" in normalized:
        return "auth_lost"
    return "failed"


__all__ = [
    "InstagramBatchScrapeRunner",
    "normalize_usernames",
]
