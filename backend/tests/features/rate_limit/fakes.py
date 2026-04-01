from __future__ import annotations

import math
from typing import Any, cast

import fakeredis.aioredis
from redis.exceptions import NoScriptError

from app.features.rate_limit.scripts import (
    SLIDING_WINDOW_SCRIPT,
    TOKEN_BUCKET_SCRIPT,
    script_sha,
)


class EvalShaFakeRedis:
    def __init__(self) -> None:
        self._redis = cast(Any, fakeredis.aioredis.FakeRedis(decode_responses=True))
        self._loaded_shas: set[str] = set()
        self.raise_on_eval: Exception | None = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._redis, name)

    async def script_load(self, script: str) -> str:
        sha = script_sha(script)
        self._loaded_shas.add(sha)
        return sha

    async def evalsha(self, sha: str, numkeys: int, *args: Any) -> object:
        if self.raise_on_eval is not None:
            raise self.raise_on_eval
        if sha not in self._loaded_shas:
            raise NoScriptError("NOSCRIPT No matching script. Please use EVAL.")
        if sha == script_sha(TOKEN_BUCKET_SCRIPT):
            return await self._run_token_bucket(numkeys, *args)
        if sha == script_sha(SLIDING_WINDOW_SCRIPT):
            return await self._run_sliding_window(numkeys, *args)
        raise AssertionError(f"Unexpected script sha: {sha}")

    async def eval(self, script: str, numkeys: int, *args: Any) -> object:
        if self.raise_on_eval is not None:
            raise self.raise_on_eval
        if script == TOKEN_BUCKET_SCRIPT:
            return await self._run_token_bucket(numkeys, *args)
        if script == SLIDING_WINDOW_SCRIPT:
            return await self._run_sliding_window(numkeys, *args)
        raise AssertionError("Unexpected Lua script.")

    async def _run_token_bucket(self, numkeys: int, *args: Any) -> list[int]:
        assert numkeys == 1
        key = str(args[0])
        now_ms = int(args[1])
        capacity = int(args[2])
        refill_tokens = int(args[3])
        refill_period_ms = int(args[4])
        cost = int(args[5])
        ttl_ms = int(args[6])
        scale = 1000
        capacity_fp = capacity * scale
        refill_fp = refill_tokens * scale
        cost_fp = cost * scale

        values = await self._redis.hmget(key, "tokens", "refilled_at_ms")
        tokens_fp = int(values[0]) if values[0] is not None else capacity_fp
        refilled_at_ms = int(values[1]) if values[1] is not None else now_ms

        elapsed_ms = max(0, now_ms - refilled_at_ms)
        if elapsed_ms > 0:
            added_fp = (elapsed_ms * refill_fp) // refill_period_ms
            if added_fp > 0:
                tokens_fp = min(capacity_fp, tokens_fp + added_fp)
                consumed_ms = (added_fp * refill_period_ms) // refill_fp
                refilled_at_ms += consumed_ms

        allowed = 0
        retry_after_seconds = 0
        if tokens_fp >= cost_fp:
            allowed = 1
            tokens_fp -= cost_fp
        else:
            missing_fp = cost_fp - tokens_fp
            retry_after_seconds = max(
                1, math.ceil((missing_fp * refill_period_ms) / refill_fp / 1000)
            )

        await self._redis.hset(
            key,
            mapping={"tokens": tokens_fp, "refilled_at_ms": refilled_at_ms},
        )
        await self._redis.pexpire(key, ttl_ms)

        remaining = tokens_fp // cost_fp
        missing_full_fp = capacity_fp - tokens_fp
        reset_after_seconds = 0
        if missing_full_fp > 0:
            reset_after_seconds = max(
                1, math.ceil((missing_full_fp * refill_period_ms) / refill_fp / 1000)
            )

        return [
            allowed,
            capacity // cost,
            remaining,
            retry_after_seconds,
            reset_after_seconds,
        ]

    async def _run_sliding_window(self, numkeys: int, *args: Any) -> list[int]:
        assert numkeys == 2
        key = str(args[0])
        sequence_key = str(args[1])
        now_ms = int(args[2])
        window_ms = int(args[3])
        max_requests = int(args[4])
        cost = int(args[5])
        ttl_ms = int(args[6])
        window_start = now_ms - window_ms

        await self._redis.zremrangebyscore(key, "-inf", window_start)
        current_count = await self._redis.zcard(key)
        allowed = 0
        retry_after_seconds = 0

        if current_count + cost <= max_requests:
            seq = int(await self._redis.incr(sequence_key))
            for index in range(cost):
                await self._redis.zadd(key, {f"{seq}:{index + 1}": now_ms})
            await self._redis.pexpire(key, ttl_ms)
            await self._redis.pexpire(sequence_key, ttl_ms)
            current_count += cost
            allowed = 1
        else:
            oldest = await self._redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                retry_after_seconds = max(
                    1, math.ceil(((int(oldest[0][1]) + window_ms) - now_ms) / 1000)
                )
            else:
                retry_after_seconds = max(1, math.ceil(window_ms / 1000))

        oldest_after = await self._redis.zrange(key, 0, 0, withscores=True)
        reset_after_seconds = 0
        if oldest_after:
            reset_after_seconds = max(
                1, math.ceil(((int(oldest_after[0][1]) + window_ms) - now_ms) / 1000)
            )

        return [
            allowed,
            max_requests // cost,
            max(0, (max_requests - current_count) // cost),
            retry_after_seconds,
            reset_after_seconds,
        ]
