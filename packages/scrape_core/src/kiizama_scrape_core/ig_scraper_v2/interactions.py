from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

from playwright.async_api import Locator, Page

Sleeper = Callable[[float], Awaitable[None]]


async def human_delay(
    min_ms: int = 300,
    max_ms: int = 800,
    *,
    sleeper: Sleeper = asyncio.sleep,
    rng: random.Random | None = None,
) -> float:
    random_source = rng or random
    delay_seconds = random_source.uniform(min_ms / 1000, max_ms / 1000)
    await sleeper(delay_seconds)
    return delay_seconds


async def human_type(
    element: Locator,
    text: str,
    *,
    min_delay_ms: int = 50,
    max_delay_ms: int = 150,
    sleeper: Sleeper = asyncio.sleep,
    rng: random.Random | None = None,
) -> None:
    for char in text:
        await element.press(char)
        await human_delay(
            min_delay_ms,
            max_delay_ms,
            sleeper=sleeper,
            rng=rng,
        )


async def human_click(
    page: Page,
    selector: str,
    *,
    max_attempts: int = 3,
    allow_double: bool = True,
    sleeper: Sleeper = asyncio.sleep,
    rng: random.Random | None = None,
    logger: logging.Logger | None = None,
) -> bool:
    random_source = rng or random
    attempts = 0
    clicks = 2 if allow_double and random_source.random() < 0.3 else 1

    while attempts < max_attempts:
        try:
            await page.wait_for_selector(selector, timeout=1000, state="visible")
            element = page.locator(selector)
            for idx in range(clicks):
                await element.first.click(timeout=2000)
                if idx + 1 < clicks:
                    await human_delay(400, 800, sleeper=sleeper, rng=rng)
            return True
        except Exception as exc:
            if logger:
                logger.debug(
                    "Failed attempt %s for %s: %s",
                    attempts + 1,
                    selector,
                    exc,
                )
            attempts += 1
            if attempts < max_attempts:
                await human_delay(500, 1000, sleeper=sleeper, rng=rng)
    return False


__all__ = [
    "Sleeper",
    "human_click",
    "human_delay",
    "human_type",
]
