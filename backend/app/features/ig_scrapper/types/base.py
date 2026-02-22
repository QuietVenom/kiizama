from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import time
import types
from collections.abc import Awaitable, Sequence
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TypeVar, cast
from urllib.parse import urlsplit

from playwright.async_api import (
    Browser,
    BrowserContext,
    ElementHandle,
    Locator,
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

from app.constants import DEFAULT_USER_AGENT

from ..classes import (
    InstagramNavigateResult,
    InstagramPost,
    InstagramProfile,
    InstagramReel,
    InstagramScrapeResult,
    InstagramSuggestedUser,
)

T = TypeVar("T")
JSONScalar = str | int | float | bool | None
JSONLike = JSONScalar | dict[str, Any] | Sequence[Any]

STEALTH_JS = r"""
(() => {
    Object.defineProperty(navigator, 'plugins', {
        get: () => [{
            name: 'Chrome PDF Plugin',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format',
            length: 1,
        }, {
            name: 'Chrome PDF Viewer',
            filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
            description: 'Portable Document Format',
            length: 1,
        }, {
            name: 'Native Client',
            filename: 'internal-nacl-plugin',
            description: 'Native Client Executable',
            length: 1,
        }],
    });

    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
    });

    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
    });

    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters)
    );

    window.chrome = {
        runtime: {},
    };
})();
"""


PLAYWRIGHT_BROWSER_INSTALL_HINT = (
    "Playwright browser executable is missing. Install Chromium with "
    "`python -m playwright install chromium` "
    "(repo shortcut: `backend/.venv/bin/python -m playwright install chromium`)."
)

# TEMP: Block heavyweight asset extensions that are not required for GraphQL data capture.
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


def _is_missing_browser_executable_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "executable doesn't exist" in message or "playwright install" in message


def _should_block_asset_request(url: str) -> bool:
    # TEMP: Filter by URL path extension only (no resource-type blocking).
    normalized_path = urlsplit(url).path.lower()
    return normalized_path.endswith(BLOCKED_ASSET_EXTENSIONS)


@dataclass(slots=True)
class NetworkUsage:
    downloaded_bytes_total: int = 0
    responses_total: int = 0
    responses_failed_to_measure: int = 0


class BaseInstagramWorker:
    """Shared Playwright orchestration and parsing helpers for Instagram flows."""

    def __init__(
        self,
        *,
        headless: bool,
        user_agent: str | None,
        locale: str,
        proxy: str | None,
        timeout_ms: int,
        measure: bool = False,
        measure_network_bytes: bool = False,
        network_usage: NetworkUsage | None = None,
    ) -> None:
        self.headless = headless
        self.user_agent = user_agent or self.default_user_agent()
        self.locale = locale
        self.proxy = proxy
        self.timeout_ms = timeout_ms
        self.measure = measure
        self.measure_network_bytes = measure_network_bytes
        self.network_usage = network_usage or NetworkUsage()

        self.logger = logging.getLogger(
            f"app.features.ig_scrapper.{self.__class__.__name__}"
        )
        self.logger.setLevel(logging.INFO)

        self._playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.timings: dict[str, int] = {}
        self._network_response_listener: Any | None = None
        self._request_blocking_enabled = False

    def get_network_usage(self) -> dict[str, int]:
        return {
            "downloaded_bytes_total": self.network_usage.downloaded_bytes_total,
            "responses_total": self.network_usage.responses_total,
            "responses_failed_to_measure": self.network_usage.responses_failed_to_measure,
        }

    # ------------------------------------------------------------------
    # Playwright lifecycle
    # ------------------------------------------------------------------
    async def __aenter__(self) -> BaseInstagramWorker:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: types.TracebackType | None,
    ) -> None:
        await self.close()

    async def start(self) -> None:
        if self._playwright is not None:
            return

        start = time.perf_counter()
        self._playwright = await async_playwright().start()
        if self.measure:
            self.timings["start_playwright_ms"] = int(
                (time.perf_counter() - start) * 1000
            )

        await self._launch_browser()
        await self._create_context()
        await self._create_page()

    async def _launch_browser(self) -> None:
        assert self._playwright is not None
        launch_options: dict[str, Any] = {
            "headless": self.headless,
            "timeout": 30000,
            "channel": "chromium",
        }
        if self.proxy:
            launch_options["proxy"] = {"server": self.proxy}

        start = time.perf_counter()
        try:
            self.browser = await self._playwright.chromium.launch(**launch_options)
        except Exception as channel_exc:
            self.logger.warning("Failed to launch Chromium channel: %s", channel_exc)
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
                raise

        if self.measure:
            self.timings["launch_browser_ms"] = int(
                (time.perf_counter() - start) * 1000
            )

    async def _create_context(self) -> None:
        assert self.browser is not None
        context_options = self.build_context_options()
        start = time.perf_counter()
        self.context = await self.browser.new_context(**context_options)
        await self._attach_request_blocking_rules()
        if self.measure_network_bytes:
            self._attach_network_usage_listener()
        if self.measure:
            self.timings["create_context_ms"] = int(
                (time.perf_counter() - start) * 1000
            )

    async def _create_page(self) -> None:
        assert self.context is not None
        start = time.perf_counter()
        self.page = await self.context.new_page()
        await self.add_stealth(self.page)
        if self.measure:
            self.timings["new_page_ms"] = int((time.perf_counter() - start) * 1000)

    async def close(self) -> None:
        if self.page:
            await self.page.close()
            self.page = None
        if self.context and self._network_response_listener is not None:
            with suppress(Exception):
                self.context.remove_listener(
                    "response", self._network_response_listener
                )
            self._network_response_listener = None
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------
    async def _attach_request_blocking_rules(self) -> None:
        if self.context is None or self._request_blocking_enabled:
            return

        # TEMP: Abort non-essential heavyweight assets to reduce network + decode overhead.
        async def _route_handler(route: Route, request: Request) -> None:
            if _should_block_asset_request(request.url):
                await route.abort()
                return
            await route.continue_()

        await self.context.route("**/*", _route_handler)
        self._request_blocking_enabled = True

    def _attach_network_usage_listener(self) -> None:
        if self.context is None or self._network_response_listener is not None:
            return

        async def _listener(response: Response) -> None:
            await self._record_downloaded_response_bytes(response)

        self._network_response_listener = _listener
        self.context.on("response", _listener)

    async def _record_downloaded_response_bytes(self, response: Response) -> None:
        self.network_usage.responses_total += 1

        try:
            raw_content_length = response.headers.get("content-length")
            if raw_content_length is not None:
                content_length = int(raw_content_length)
            else:
                content_length = len(await response.body())
        except Exception:
            self.network_usage.responses_failed_to_measure += 1
            return

        if content_length > 0:
            self.network_usage.downloaded_bytes_total += content_length

    def build_context_options(self) -> dict[str, Any]:
        return {
            "user_agent": self.user_agent,
            "locale": self.locale,
            "viewport": {"width": 1366, "height": 882},
            "ignore_https_errors": True,
        }

    async def timed(self, key: str, awaitable: Awaitable[Any]) -> Any:
        start = time.perf_counter()
        try:
            return await awaitable
        finally:
            if self.measure:
                self.timings[key] = int((time.perf_counter() - start) * 1000)

    # ------------------------------------------------------------------
    # Interaction helpers
    # ------------------------------------------------------------------
    @staticmethod
    def default_user_agent() -> str:
        return DEFAULT_USER_AGENT

    @staticmethod
    async def add_stealth(page: Page) -> None:
        try:
            await page.add_init_script(STEALTH_JS)
            await page.set_extra_http_headers(
                {
                    "Accept-Language": "en-US,en;q=0.9",
                    "Sec-Ch-Ua": '"Chromium";v="139", "Google Chrome";v="139", "Not-A.Brand";v="99"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"macOS"',
                }
            )
        except Exception as exc:
            logging.getLogger("app.features.ig_scrapper.stealth").warning(
                "Failed to add stealth script: %s", exc
            )

    @staticmethod
    async def human_delay(min_ms: int = 300, max_ms: int = 800) -> None:
        await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))

    async def human_type(
        self,
        element: Locator,
        text: str,
        *,
        min_delay: int = 50,
        max_delay: int = 150,
    ) -> None:
        for char in text:
            await element.press(char)
            await self.human_delay(min_delay, max_delay)

    async def human_click(
        self,
        page: Page,
        selector: str,
        *,
        max_attempts: int = 3,
        allow_double: bool = True,
    ) -> bool:
        attempts = 0
        clicks = 2 if allow_double and random.random() < 0.3 else 1

        while attempts < max_attempts:
            try:
                await page.wait_for_selector(selector, timeout=1000, state="visible")
                element = page.locator(selector)
                for idx in range(clicks):
                    await element.first.click(timeout=2000)
                    if idx + 1 < clicks:
                        await self.human_delay(400, 800)
                return True
            except Exception as exc:
                self.logger.debug(
                    "Failed attempt %s for %s: %s", attempts + 1, selector, exc
                )
                attempts += 1
                if attempts < max_attempts:
                    await self.human_delay(500, 1000)
        return False

    async def collect_reels_tab(
        self,
        page: Page,
        username: str,
        reels_done_event: asyncio.Event,
    ) -> None:
        user_slug = username.strip().strip("/")
        if not user_slug:
            reels_done_event.set()
            return

        reels_selectors = [
            f"a[href='/{user_slug}/reels/']",
            "a[href$='/reels/']",
            "a[role='link'][href*='/reels/']",
        ]

        reels_clicked = False
        for selector in reels_selectors:
            try:
                await page.wait_for_selector(selector, timeout=4000)
                if await self.human_click(page, selector, allow_double=False):
                    reels_clicked = True
                    break
            except Exception:
                continue

        if not reels_clicked:
            reels_done_event.set()
            return

        try:
            await page.wait_for_url("**/reels/**", timeout=10000)
        except Exception:
            pass

        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
            await asyncio.sleep(1)
        except Exception:
            pass

        await asyncio.wait_for(reels_done_event.wait(), timeout=15)

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------
    @staticmethod
    def dig(obj: JSONLike, path: str, default: T | None = None) -> T | None:
        cur: JSONLike = obj
        for part in path.split("."):
            if isinstance(cur, dict):
                if part in cur:
                    cur = cast(JSONLike, cur[part])
                else:
                    return default
            elif isinstance(cur, Sequence) and not isinstance(
                cur, str | bytes | bytearray
            ):
                try:
                    idx = int(part)
                except ValueError:
                    return default
                if 0 <= idx < len(cur):
                    cur = cast(JSONLike, cur[idx])
                else:
                    return default
            else:
                return default
            if cur is None:
                return default
        return cast(T | None, cur)

    @staticmethod
    def safe_cast_to_dict(
        obj: Any, default: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if default is None:
            default = {}
        return cast(dict[str, Any], obj) if isinstance(obj, dict) else default

    @staticmethod
    def safe_cast_to_list(obj: Any, default: list[Any] | None = None) -> list[Any]:
        if default is None:
            default = []
        return obj if isinstance(obj, list) else default

    @staticmethod
    def extract_coauthors(coauthors_data: Any) -> list[str]:
        result: list[str] = []
        if not isinstance(coauthors_data, list):
            return result
        for item in coauthors_data:
            if isinstance(item, dict):
                username = item.get("username")
                if isinstance(username, str):
                    result.append(username)
        return result

    @staticmethod
    def extract_usertags(usertags_data: Any) -> list[str]:
        result: list[str] = []
        if not isinstance(usertags_data, dict):
            return result
        inner = usertags_data.get("in")
        if not isinstance(inner, list):
            return result
        for tag in inner:
            if isinstance(tag, dict):
                user_obj = tag.get("user")
                if isinstance(user_obj, dict):
                    username = user_obj.get("username")
                    if isinstance(username, str):
                        result.append(username)
        return result

    def parse_post_info(self, node: dict[str, Any]) -> InstagramPost:
        post = InstagramPost()
        if not node:
            return post

        code = node.get("code") or node.get("shortcode")
        if isinstance(code, str):
            post.code = code

        caption_raw = node.get("caption")
        if isinstance(caption_raw, dict):
            text_any = caption_raw.get("text")
            if isinstance(text_any, str):
                post.caption_text = text_any

        if "is_paid_partnership" in node:
            post.is_paid_partnership = node.get("is_paid_partnership")

        if "sponsor_tags" in node:
            post.sponsor_tags = node.get("sponsor_tags")

        coauthors = self.extract_coauthors(node.get("coauthor_producers"))
        if coauthors:
            post.coauthor_producers = coauthors

        for field in ("comment_count", "like_count"):
            value = node.get(field)
            if isinstance(value, int):
                setattr(post, field, value)

        utags = self.extract_usertags(node.get("usertags"))
        if utags:
            post.usertags = utags

        timestamp = node.get("taken_at_timestamp")
        if isinstance(timestamp, int):
            post.timestamp = timestamp

        media_type = node.get("media_type")
        if isinstance(media_type, int):
            post.media_type = media_type

        product_type = node.get("product_type")
        if isinstance(product_type, str):
            post.product_type = product_type

        return post

    def parse_user_info(self, user_data: dict[str, Any]) -> InstagramProfile:
        profile = InstagramProfile()
        if not user_data:
            return profile

        mapping: tuple[tuple[str, type], ...] = (
            ("id", str),
            ("username", str),
            ("full_name", str),
            ("profile_pic_url", str),
            ("biography", str),
            ("is_private", bool),
            ("is_regulated_c18", bool),
            ("is_verified", bool),
            ("account_type", int),
            ("follower_count", int),
            ("following_count", int),
            ("media_count", int),
            ("external_url", str),
            ("category_name", str),
            ("has_guides", bool),
        )

        for field, expected in mapping:
            value = user_data.get(field)
            if isinstance(value, expected):
                setattr(profile, field, value)

        bio_links = user_data.get("bio_links")
        if isinstance(bio_links, list):
            profile.bio_links = cast(list[dict[str, Any]], bio_links)

        return profile

    def parse_suggested_users(
        self, users_data: list[dict[str, Any]]
    ) -> list[InstagramSuggestedUser]:
        result: list[InstagramSuggestedUser] = []
        for item in users_data:
            if not isinstance(item, dict):
                continue

            candidate = item
            while isinstance(candidate, dict):
                nested_candidate: dict[str, Any] | None = None
                for nested_key in ("user", "node", "profile"):
                    nested = candidate.get(nested_key)
                    if isinstance(nested, dict):
                        nested_candidate = nested
                        break
                if nested_candidate is None:
                    break
                candidate = nested_candidate

            suggested = InstagramSuggestedUser()
            username = candidate.get("username")
            if isinstance(username, str):
                suggested.username = username

            raw_id = candidate.get("id")
            if raw_id is None:
                raw_id = candidate.get("pk")
            if isinstance(raw_id, str | int):
                suggested.id = str(raw_id)

            full_name = candidate.get("full_name")
            if isinstance(full_name, str):
                suggested.full_name = full_name

            profile_pic_url = candidate.get("profile_pic_url")
            if not isinstance(profile_pic_url, str):
                profile_pic_url = candidate.get("profile_pic_url_hd")
            if isinstance(profile_pic_url, str):
                suggested.profile_pic_url = profile_pic_url

            if any(
                getattr(suggested, attr) is not None
                for attr in ("username", "id", "full_name", "profile_pic_url")
            ):
                result.append(suggested)
        return result

    @staticmethod
    def get_safe_filename(username: str, result: InstagramScrapeResult) -> str:
        base_name = result.user.username or username or "profile"
        safe_name = "".join(c for c in base_name if c.isalnum() or c in (" ", "-", "_"))
        return safe_name.strip().replace(" ", "_").replace("-", "_")

    @staticmethod
    def dump_json(
        payload: InstagramScrapeResult | InstagramNavigateResult, path: Path
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, InstagramNavigateResult):
            data = asdict(payload)
        else:
            data = asdict(payload)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return path

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------
    def build_scrape_result(
        self,
        *,
        user: dict[str, Any] | None = None,
        recommended: list[InstagramSuggestedUser] | None = None,
        posts: list[InstagramPost] | None = None,
        reels: list[InstagramReel] | None = None,
        success: bool | None = None,
        error: str | None = None,
    ) -> InstagramScrapeResult:
        result = InstagramScrapeResult()
        if user:
            result.user = self.parse_user_info(user)
        if recommended is not None:
            result.recommended_users = recommended
        if posts is not None:
            result.posts = posts
        if reels is not None:
            result.reels = reels
        if success is not None:
            result.success = success
        result.error = error
        return result

    async def profile_not_found(self, page: Page, timeout_ms: int = 1500) -> bool:
        """Return True when Instagram displays the unavailable message."""
        unavailable_texts = (
            "profile isn't available",
            "profile no disponible",
            "profile no está disponible",
            "profile not available",
            "sorry, this page isn't available",
            "sorry, this page isn't available.",
            "the link you followed may be broken",
            "this page isn't available",
        )

        # Regex con tus mismos textos, case-insensitive
        unavailable_regex = re.compile(
            "|".join(re.escape(t) for t in unavailable_texts),
            re.IGNORECASE,
        )

        # Buscar primero el texto dentro del <main> (menos ruido que spans globales)
        main = page.locator("main")
        hit = main.get_by_text(unavailable_regex).first

        try:
            # Espera corta para que aparezca (evita falsos negativos por render async)
            await hit.wait_for(state="visible", timeout=timeout_ms)
            return True
        except PlaywrightTimeoutError:
            pass
        except Exception:
            pass

        # Fallback 1: revisar texto completo del <main> por si el nodo no fue visible
        # al primer intento.
        try:
            main_text = await main.inner_text(timeout=timeout_ms)
            if unavailable_regex.search(main_text):
                return True
        except Exception:
            pass

        return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (PlaywrightTimeoutError, asyncio.TimeoutError, ConnectionError)
        ),
        reraise=True,
    )
    async def retryable_goto(
        self, page: Page, url: str, **kwargs: Any
    ) -> Response | None:
        """Retryable version of page.goto with exponential backoff."""
        return await page.goto(url, **kwargs)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (PlaywrightTimeoutError, asyncio.TimeoutError, ConnectionError)
        ),
        reraise=True,
    )
    async def retryable_click(self, page: Page, selector: str, **kwargs: Any) -> bool:
        """Retryable version of human_click with exponential backoff."""
        return await self.human_click(page, selector, **kwargs)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (PlaywrightTimeoutError, asyncio.TimeoutError, ConnectionError)
        ),
        reraise=True,
    )
    async def retryable_wait_for_selector(
        self, page: Page, selector: str, **kwargs: Any
    ) -> ElementHandle | None:
        """Retryable version of page.wait_for_selector with exponential backoff."""
        return await page.wait_for_selector(selector, **kwargs)


__all__ = ["BaseInstagramWorker", "NetworkUsage"]
