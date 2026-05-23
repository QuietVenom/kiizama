from __future__ import annotations

import random
from collections.abc import Awaitable, Callable

from .config import PacingConfig

Sleeper = Callable[[float], Awaitable[None]]


def next_delay_seconds(
    config: PacingConfig,
    *,
    rng: random.Random | None = None,
) -> float:
    if not config.enabled:
        return 0.0

    random_source = rng or random
    return random_source.uniform(config.min_delay_seconds, config.max_delay_seconds)


def warmup_delay_seconds(config: PacingConfig) -> float:
    if not config.enabled:
        return 0.0

    random_source = random
    return random_source.uniform(config.warmup_min_seconds, config.warmup_max_seconds)


def next_warmup_delay_seconds(
    config: PacingConfig,
    *,
    rng: random.Random | None = None,
) -> float:
    if not config.enabled:
        return 0.0

    random_source = rng or random
    return random_source.uniform(config.warmup_min_seconds, config.warmup_max_seconds)


async def sleep_for_next_delay(
    config: PacingConfig,
    *,
    sleeper: Sleeper,
    rng: random.Random | None = None,
) -> float:
    delay_seconds = next_delay_seconds(config, rng=rng)
    if delay_seconds > 0:
        await sleeper(delay_seconds)
    return delay_seconds


async def sleep_for_warmup(
    config: PacingConfig,
    *,
    sleeper: Sleeper,
    rng: random.Random | None = None,
) -> float:
    delay_seconds = next_warmup_delay_seconds(config, rng=rng)
    if delay_seconds > 0:
        await sleeper(delay_seconds)
    return delay_seconds


__all__ = [
    "Sleeper",
    "next_warmup_delay_seconds",
    "next_delay_seconds",
    "sleep_for_next_delay",
    "sleep_for_warmup",
    "warmup_delay_seconds",
]
