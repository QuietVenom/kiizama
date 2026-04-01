from __future__ import annotations

import hashlib
from collections.abc import Sequence

from redis.exceptions import NoScriptError

from app.core.redis import RedisClient

TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local refill_tokens = tonumber(ARGV[3])
local refill_period_ms = tonumber(ARGV[4])
local cost = tonumber(ARGV[5])
local ttl_ms = tonumber(ARGV[6])
local scale = 1000

local capacity_fp = capacity * scale
local refill_fp = refill_tokens * scale
local cost_fp = cost * scale

local values = redis.call('HMGET', key, 'tokens', 'refilled_at_ms')
local tokens_fp = tonumber(values[1])
local refilled_at_ms = tonumber(values[2])

if tokens_fp == nil then
  tokens_fp = capacity_fp
  refilled_at_ms = now_ms
end

local elapsed_ms = math.max(0, now_ms - refilled_at_ms)
if elapsed_ms > 0 then
  local added_fp = math.floor((elapsed_ms * refill_fp) / refill_period_ms)
  if added_fp > 0 then
    tokens_fp = math.min(capacity_fp, tokens_fp + added_fp)
    local consumed_ms = math.floor((added_fp * refill_period_ms) / refill_fp)
    refilled_at_ms = refilled_at_ms + consumed_ms
  end
end

local allowed = 0
local retry_after_seconds = 0
if tokens_fp >= cost_fp then
  allowed = 1
  tokens_fp = tokens_fp - cost_fp
else
  local missing_fp = cost_fp - tokens_fp
  retry_after_seconds = math.max(
    1,
    math.ceil((missing_fp * refill_period_ms) / refill_fp / 1000)
  )
end

redis.call('HSET', key, 'tokens', tokens_fp, 'refilled_at_ms', refilled_at_ms)
redis.call('PEXPIRE', key, ttl_ms)

local remaining = math.floor(tokens_fp / cost_fp)
local missing_full_fp = capacity_fp - tokens_fp
local reset_after_seconds = 0
if missing_full_fp > 0 then
  reset_after_seconds = math.max(
    1,
    math.ceil((missing_full_fp * refill_period_ms) / refill_fp / 1000)
  )
end

return {allowed, capacity / cost, remaining, retry_after_seconds, reset_after_seconds}
""".strip()

SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local sequence_key = KEYS[2]
local now_ms = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local max_requests = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
local ttl_ms = tonumber(ARGV[5])

local window_start = now_ms - window_ms
redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

local current_count = redis.call('ZCARD', key)
local allowed = 0
local retry_after_seconds = 0

if current_count + cost <= max_requests then
  local seq = redis.call('INCR', sequence_key)
  for i = 1, cost do
    redis.call('ZADD', key, now_ms, tostring(seq) .. ':' .. tostring(i))
  end
  redis.call('PEXPIRE', key, ttl_ms)
  redis.call('PEXPIRE', sequence_key, ttl_ms)
  current_count = current_count + cost
  allowed = 1
else
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  if oldest[2] ~= nil then
    retry_after_seconds = math.max(
      1,
      math.ceil(((tonumber(oldest[2]) + window_ms) - now_ms) / 1000)
    )
  else
    retry_after_seconds = math.max(1, math.ceil(window_ms / 1000))
  end
end

local oldest_after = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
local reset_after_seconds = 0
if oldest_after[2] ~= nil then
  reset_after_seconds = math.max(
    1,
    math.ceil(((tonumber(oldest_after[2]) + window_ms) - now_ms) / 1000)
  )
end

return {allowed, max_requests / cost, math.max(0, (max_requests - current_count) / cost), retry_after_seconds, reset_after_seconds}
""".strip()

SCRIPTS = {
    "token_bucket": TOKEN_BUCKET_SCRIPT,
    "sliding_window": SLIDING_WINDOW_SCRIPT,
}


def script_sha(script: str) -> str:
    return hashlib.sha1(script.encode("utf-8")).hexdigest()


class RedisScriptLoader:
    def __init__(self) -> None:
        self._sha_by_name = {
            name: script_sha(source) for name, source in SCRIPTS.items()
        }

    async def execute(
        self,
        redis: RedisClient,
        *,
        name: str,
        keys: Sequence[str],
        args: Sequence[int | str],
    ) -> object:
        source = SCRIPTS[name]
        sha = self._sha_by_name[name]
        try:
            return await redis.evalsha(sha, len(keys), *keys, *args)
        except NoScriptError:
            loaded_sha = await redis.script_load(source)
            self._sha_by_name[name] = loaded_sha
            return await redis.evalsha(loaded_sha, len(keys), *keys, *args)
        except AttributeError:
            return await redis.eval(source, len(keys), *keys, *args)


script_loader = RedisScriptLoader()
