from __future__ import annotations

import asyncio
import logging
import random
import time
import types
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Request,
    Response,
    Route,
    async_playwright,
)
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import ScraperV2Config
from .interactions import Sleeper
from .logging_utils import (
    proxy_mode_label,
    redacted_identifier,
    sanitize_exception_for_log,
    sanitize_log_value,
)
from .pacing import sleep_for_warmup
from .stealth import add_stealth, merge_extra_headers

PLAYWRIGHT_BROWSER_INSTALL_HINT = (
    "Playwright browser executable is missing. Install Chromium with "
    "`python -m playwright install chromium` "
    "(repo shortcut: `backend/.venv/bin/python -m playwright install chromium`)."
)

BLOCKED_ASSET_EXTENSIONS: tuple[str, ...] = (
    ".mp4",
    ".m3u8",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".avif",
    ".gif",
)


class PlaywrightBrowserNotInstalledError(RuntimeError):
    """Raised when Playwright browser binaries are unavailable at runtime."""


@dataclass(slots=True)
class BrowserSessionTimings:
    start_playwright_ms: int | None = None
    launch_browser_ms: int | None = None
    create_context_ms: int | None = None
    new_page_ms: int | None = None
    cold_warmup_seconds: float | None = None
    selected_proxy_url: str | None = None


@dataclass
class InstagramBrowserSession:
    config: ScraperV2Config
    storage_state: dict[str, Any] | None = None
    extra_http_headers: dict[str, str] | None = None
    credential_id: str | None = None
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger(
            "kiizama_scrape_core.ig_scraper_v2.browser"
        )
    )
    sleeper: Sleeper = asyncio.sleep
    rng: random.Random | None = None

    def __post_init__(self) -> None:
        self._playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.timings = BrowserSessionTimings()
        self._request_blocking_enabled = False

    async def __aenter__(self) -> InstagramBrowserSession:
        await self.start(credential_id=self.credential_id)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: types.TracebackType | None,
    ) -> None:
        await self.close()

    async def start(self, *, credential_id: str | None = None) -> None:
        if self._playwright is not None:
            return

        start = time.perf_counter()
        self._playwright = await async_playwright().start()
        self.timings.start_playwright_ms = _elapsed_ms(start)

        await self._launch_browser()
        await self._create_context()
        await self._create_page()
        await self.cold_warm_up(credential_id=credential_id)

    async def _launch_browser(self) -> None:
        assert self._playwright is not None
        launch_options = self.build_launch_options()

        start = time.perf_counter()
        try:
            self.browser = await self._playwright.chromium.launch(**launch_options)
        except Exception as channel_exc:
            self.logger.warning(
                "Failed to launch Chromium channel: %s",
                sanitize_log_value(channel_exc),
            )
            launch_options.pop("channel", None)
            try:
                self.browser = await self._playwright.chromium.launch(**launch_options)
            except Exception as launch_exc:
                if _is_missing_browser_executable_error(
                    channel_exc
                ) or _is_missing_browser_executable_error(launch_exc):
                    raise PlaywrightBrowserNotInstalledError(
                        PLAYWRIGHT_BROWSER_INSTALL_HINT
                    ) from launch_exc
                _sanitize_exception_for_log_reraise(launch_exc)
                raise

        self.timings.launch_browser_ms = _elapsed_ms(start)

    def build_launch_options(self) -> dict[str, Any]:
        launch_options: dict[str, Any] = {
            "headless": self.config.browser.headless,
            "timeout": 30_000,
            "channel": "chromium",
        }
        # TODO: Run a DECODO smoke test before enabling worker usage:
        # verify proxy mode, warm-up timing, session persistence, and log redaction.
        proxy_url = self.select_proxy_url()
        if proxy_url:
            launch_options["proxy"] = {"server": proxy_url}
            self.timings.selected_proxy_url = proxy_url
        return launch_options

    def select_proxy_url(self) -> str | None:
        if not self.config.proxy.use_isp_proxy:
            return None
        proxy_urls = self.config.proxy.proxy_urls
        if len(proxy_urls) == 1:
            return proxy_urls[0]
        random_source = self.rng or random
        return random_source.choice(proxy_urls)

    async def _create_context(self) -> None:
        assert self.browser is not None
        context_options = self.build_context_options()
        start = time.perf_counter()
        self.context = await self.browser.new_context(**context_options)
        await self._attach_request_blocking_rules()
        self.timings.create_context_ms = _elapsed_ms(start)

    def build_context_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {
            "user_agent": self.config.browser.user_agent,
            "locale": self.config.browser.locale,
            "viewport": {
                "width": self.config.browser.viewport_width,
                "height": self.config.browser.viewport_height,
            },
            "ignore_https_errors": True,
            "extra_http_headers": merge_extra_headers(
                locale=self.config.browser.locale,
                extra_headers=self.extra_http_headers,
            ),
        }
        if self.storage_state:
            options["storage_state"] = self.storage_state
        return options

    async def _create_page(self) -> None:
        assert self.context is not None
        start = time.perf_counter()
        self.page = await self.context.new_page()
        await add_stealth(
            self.page,
            locale=self.config.browser.locale,
            logger=self.logger,
        )
        self.timings.new_page_ms = _elapsed_ms(start)

    async def cold_warm_up(self, *, credential_id: str | None = None) -> float:
        delay_seconds = await sleep_for_warmup(
            self.config.pacing,
            sleeper=self.sleeper,
            rng=self.rng,
        )
        self.timings.cold_warmup_seconds = delay_seconds
        if delay_seconds > 0:
            self.logger.info(
                "Completed cold browser warm-up before Instagram navigation "
                "(seconds=%.2f, proxy_mode=%s, credential_id=%s)",
                delay_seconds,
                proxy_mode_label(self.config),
                redacted_identifier(credential_id),
            )
        return delay_seconds

    async def close(self) -> None:
        if self.page:
            await self.page.close()
            self.page = None
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def _attach_request_blocking_rules(self) -> None:
        if self.context is None or self._request_blocking_enabled:
            return

        async def route_handler(route: Route, request: Request) -> None:
            if _should_block_asset_request(request.url):
                await route.abort()
                return
            await route.continue_()

        await self.context.route("**/*", route_handler)
        self._request_blocking_enabled = True

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (PlaywrightTimeoutError, asyncio.TimeoutError, ConnectionError)
        ),
        reraise=True,
    )
    async def retryable_goto(
        self,
        page: Page,
        url: str,
        **kwargs: Any,
    ) -> Response | None:
        return await page.goto(url, **kwargs)


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _is_missing_browser_executable_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "executable doesn't exist" in message or "playwright install" in message


def _sanitize_exception_for_log_reraise(exc: Exception) -> None:
    sanitize_exception_for_log(exc)


def _should_block_asset_request(url: str) -> bool:
    normalized_path = urlsplit(url).path.lower()
    return normalized_path.endswith(BLOCKED_ASSET_EXTENSIONS)


__all__ = [
    "BrowserSessionTimings",
    "InstagramBrowserSession",
    "PlaywrightBrowserNotInstalledError",
]
