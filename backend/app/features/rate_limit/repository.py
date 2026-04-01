from __future__ import annotations

import time
from collections.abc import Callable
from typing import cast

from app.core.redis import RedisClient, get_redis_client

from .keys import build_rate_limit_key, build_rate_limit_sequence_key
from .schemas import RateLimitAlgorithm, RateLimitDecision, RateLimitRule
from .scripts import script_loader

TOKEN_BUCKET_TTL_BUFFER_SECONDS = 60
SLIDING_WINDOW_TTL_BUFFER_SECONDS = 60


class RateLimitRepository:
    def __init__(
        self,
        *,
        redis_provider: Callable[[], RedisClient] = get_redis_client,
    ) -> None:
        self._redis_provider = redis_provider

    def require_redis_client(self) -> RedisClient:
        return self._redis_provider()

    async def evaluate_rule(
        self,
        *,
        policy_name: str,
        subject: str,
        rule: RateLimitRule,
        now_ms: int | None = None,
    ) -> RateLimitDecision:
        current_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        redis = self.require_redis_client()
        key = build_rate_limit_key(policy_name=policy_name, subject=subject)

        if rule.algorithm is RateLimitAlgorithm.TOKEN_BUCKET:
            assert rule.capacity is not None
            assert rule.refill_tokens is not None
            assert rule.refill_period_seconds is not None
            ttl_ms = (
                ((rule.capacity * rule.refill_period_seconds) // rule.refill_tokens)
                + TOKEN_BUCKET_TTL_BUFFER_SECONDS
            ) * 1000
            raw = await script_loader.execute(
                redis,
                name="token_bucket",
                keys=[key],
                args=[
                    current_ms,
                    rule.capacity,
                    rule.refill_tokens,
                    rule.refill_period_seconds * 1000,
                    rule.cost,
                    ttl_ms,
                ],
            )
        else:
            assert rule.window_seconds is not None
            assert rule.max_requests is not None
            raw = await script_loader.execute(
                redis,
                name="sliding_window",
                keys=[
                    key,
                    build_rate_limit_sequence_key(
                        policy_name=policy_name,
                        subject=subject,
                    ),
                ],
                args=[
                    current_ms,
                    rule.window_seconds * 1000,
                    rule.max_requests,
                    rule.cost,
                    (rule.window_seconds + SLIDING_WINDOW_TTL_BUFFER_SECONDS) * 1000,
                ],
            )

        allowed, limit, remaining, retry_after, reset_after = cast(list[object], raw)
        return RateLimitDecision(
            allowed=bool(int(cast(int | str, allowed))),
            limit=int(cast(int | str, limit)),
            remaining=int(cast(int | str, remaining)),
            retry_after_seconds=int(cast(int | str, retry_after)),
            reset_after_seconds=int(cast(int | str, reset_after)),
            rule=rule.name,
        )
