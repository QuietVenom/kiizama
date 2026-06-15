from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from playwright.async_api import Page

from .classes import InstagramScrapeResult
from .config import ScraperV2Config
from .interactions import Sleeper, human_click
from .logging_utils import sanitize_log_value
from .parsers import dig, find_profile_user_data, parse_user_info
from .profile_navigation import InstagramProfileNavigator, profile_not_found
from .scrape_collector import InstagramScrapeCollector


class InstagramProfileScraper:
    def __init__(
        self,
        *,
        config: ScraperV2Config,
        navigator: InstagramProfileNavigator,
        max_posts: int,
        logger: logging.Logger | None = None,
        sleeper: Sleeper = asyncio.sleep,
        rng: random.Random | None = None,
    ) -> None:
        self.config = config
        self.navigator = navigator
        self.max_posts = max_posts
        self.logger = logger or logging.getLogger(
            "kiizama_scrape_core.ig_scraper_v2.profile_scraper"
        )
        self.sleeper = sleeper
        self.rng = rng or random.Random()

    async def scrape(self, page: Page, username: str) -> InstagramScrapeResult:
        scrape_result = InstagramScrapeResult()
        collector = InstagramScrapeCollector(
            max_posts=self.max_posts,
            target_username=username,
            logger=self.logger,
            collect_posts=True,
            collect_reels=True,
        )
        collector.attach(page)

        try:
            open_result = await self.navigator.open_profile(page, username)
            if not open_result.success:
                scrape_result.success = False
                scrape_result.error = open_result.error
                return scrape_result

            posts_ready = await self._wait_for_posts_data(
                page=page,
                username=username,
                collector=collector,
            )
            if posts_ready:
                try:
                    await collect_reels_tab(
                        page,
                        username,
                        collector.reels_done_event,
                        sleeper=self.sleeper,
                        rng=self.rng,
                    )
                except TimeoutError:
                    self.logger.warning(
                        "Timeout waiting for reels data for %s", username
                    )
            else:
                self.logger.info(
                    "Skipping reels collection for %s due to missing GraphQL data",
                    username,
                )
        except Exception as exc:
            sanitized_error = sanitize_log_value(exc)
            self.logger.error(
                "Error during profile scraping for %s: %s",
                username,
                sanitized_error,
            )
            scrape_result.error = f"Error during profile scraping: {sanitized_error}"
            scrape_result.success = False
        finally:
            collector.detach(page)

        if not collector.user_info:
            collector.user_info = await extract_user_info_from_scripts(
                page,
                target_username=username,
            )

        scrape_result.user = parse_user_info(collector.user_info or {})
        scrape_result.recommended_users = collector.recommended_users
        scrape_result.posts = collector.posts
        scrape_result.reels = collector.reels
        scrape_result.success = bool(scrape_result.user.username)
        if not scrape_result.success and scrape_result.error is None:
            if await profile_not_found(page):
                scrape_result.error = "Instagram username does not exist"
            else:
                scrape_result.error = "Unable to collect profile data for this username"
        return scrape_result

    async def _wait_for_posts_data(
        self,
        *,
        page: Page,
        username: str,
        collector: InstagramScrapeCollector,
    ) -> bool:
        try:
            await asyncio.wait_for(
                collector.posts_ready_event.wait(),
                timeout=self.config.browser.timeout_ms / 1000,
            )
            return True
        except TimeoutError:
            pass

        try:
            await page.reload(
                wait_until="domcontentloaded",
                timeout=self.config.browser.timeout_ms,
            )
            await asyncio.wait_for(collector.posts_ready_event.wait(), timeout=5)
            return True
        except Exception as refresh_exc:
            self.logger.debug(
                "Refresh after GraphQL timeout failed for %s: %s",
                username,
                sanitize_log_value(refresh_exc),
            )

        self.logger.warning("Timeout waiting for GraphQL data for %s", username)
        return False


async def collect_reels_tab(
    page: Page,
    username: str,
    reels_done_event: asyncio.Event,
    *,
    sleeper: Sleeper = asyncio.sleep,
    rng: random.Random | None = None,
) -> None:
    user_slug = username.strip().strip("/")
    if not user_slug:
        reels_done_event.set()
        return

    reels_selectors = (
        f"a[href='/{user_slug}/reels/']",
        "a[href$='/reels/']",
        "a[role='link'][href*='/reels/']",
    )
    reels_clicked = False
    for selector in reels_selectors:
        try:
            await page.wait_for_selector(selector, timeout=4000)
            if await human_click(
                page,
                selector,
                allow_double=False,
                sleeper=sleeper,
                rng=rng,
            ):
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
        await sleeper(1)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
        await sleeper(1)
    except Exception:
        pass

    await asyncio.wait_for(reels_done_event.wait(), timeout=15)


async def extract_user_info_from_scripts(
    page: Page,
    *,
    target_username: str | None = None,
) -> dict[str, Any] | None:
    try:
        script_content = await page.evaluate(
            """
            () => {
                const scripts = document.querySelectorAll('script[type="application/json"]');
                const parsed = [];
                for (const script of scripts) {
                    try {
                        const data = JSON.parse(script.textContent);
                        if (data.entry_data && data.entry_data.ProfilePage) {
                            return data;
                        }
                        parsed.push(data);
                    } catch (e) {}
                }
                return parsed;
            }
            """
        )
    except Exception:
        return None

    if not script_content:
        return None
    profile_pages = dig(script_content, "entry_data.ProfilePage")
    if isinstance(profile_pages, list) and profile_pages:
        user_data = dig(profile_pages[0], "graphql.user")
        if isinstance(user_data, dict):
            return user_data
    return find_profile_user_data(
        script_content,
        target_username=target_username,
    )


__all__ = [
    "InstagramProfileScraper",
    "collect_reels_tab",
    "extract_user_info_from_scripts",
]
