from __future__ import annotations

from collections.abc import Callable

from redis.exceptions import RedisError

from kiizama_scrape_core.redis import RedisClient

from .schemas import UserEventEnvelope, UserStreamEntry

USER_EVENTS_STREAM_PREFIX = "user:events:stream:"
STREAM_EVENT_FIELD = "event"
STREAM_NOTIFICATION_ID_FIELD = "notification_id"
STREAM_PAYLOAD_FIELD = "payload"

PUBLISH_USER_EVENT_SCRIPT = """
local dedupe_enabled = ARGV[1] == '1'
local dedupe_ttl_seconds = tonumber(ARGV[2]) or 0
local stream_ttl_seconds = tonumber(ARGV[3]) or 0

if dedupe_enabled then
  local existing = redis.call('GET', KEYS[2])
  if existing then
    return {existing, '0'}
  end
end

local event_id = redis.call(
  'XADD',
  KEYS[1],
  'MAXLEN',
  ARGV[4],
  '*',
  ARGV[5],
  ARGV[6],
  ARGV[7],
  ARGV[8],
  ARGV[9],
  ARGV[10]
)

if stream_ttl_seconds > 0 then
  redis.call('EXPIRE', KEYS[1], stream_ttl_seconds)
end

if dedupe_enabled then
  redis.call('SET', KEYS[2], event_id, 'EX', dedupe_ttl_seconds)
end

return {event_id, '1'}
"""


class UserEventsUnavailableError(RuntimeError):
    """Raised when Redis is unavailable for user events."""


def build_user_events_stream_key(user_id: str) -> str:
    return f"{USER_EVENTS_STREAM_PREFIX}{user_id}"


class UserEventsRepository:
    def __init__(
        self,
        *,
        redis_provider: Callable[[], RedisClient],
        stream_maxlen: int,
        stream_ttl_seconds: int,
    ) -> None:
        self._redis_provider = redis_provider
        self._stream_maxlen = stream_maxlen
        self._stream_ttl_seconds = stream_ttl_seconds

    def require_redis_client(self) -> RedisClient:
        try:
            return self._redis_provider()
        except RuntimeError as exc:
            raise UserEventsUnavailableError(str(exc)) from exc

    def assert_available(self) -> None:
        self.require_redis_client()

    async def publish_event(
        self,
        *,
        user_id: str,
        event_name: str,
        envelope: UserEventEnvelope,
        dedupe_key: str | None = None,
        dedupe_ttl_seconds: int | None = None,
    ) -> tuple[str, bool]:
        if dedupe_key and (dedupe_ttl_seconds is None or dedupe_ttl_seconds <= 0):
            raise ValueError(
                "dedupe_ttl_seconds must be positive when dedupe_key is set."
            )

        redis = self.require_redis_client()
        dedupe_ttl = dedupe_ttl_seconds or 0
        keys = [build_user_events_stream_key(user_id)]
        if dedupe_key:
            keys.append(dedupe_key)

        try:
            result = await redis.eval(
                PUBLISH_USER_EVENT_SCRIPT,
                len(keys),
                *keys,
                "1" if dedupe_key else "0",
                str(dedupe_ttl),
                str(self._stream_ttl_seconds),
                str(self._stream_maxlen),
                STREAM_EVENT_FIELD,
                event_name,
                STREAM_NOTIFICATION_ID_FIELD,
                envelope.notification_id,
                STREAM_PAYLOAD_FIELD,
                envelope.model_dump_json(),
            )
        except RedisError as exc:
            raise UserEventsUnavailableError(
                "Redis is unavailable for user events."
            ) from exc

        if not isinstance(result, list) or len(result) != 2:
            raise RuntimeError("Unexpected Redis user event publish result.")

        event_id = str(result[0])
        published = str(result[1]) == "1"
        return event_id, published

    async def delete_user_stream(self, *, user_id: str) -> None:
        redis = self.require_redis_client()

        try:
            await redis.delete(build_user_events_stream_key(user_id))
        except RedisError as exc:
            raise UserEventsUnavailableError(
                "Redis is unavailable for user events."
            ) from exc

    async def read_events(
        self,
        *,
        user_id: str,
        cursor: str,
        block_ms: int,
        count: int = 10,
    ) -> list[UserStreamEntry]:
        redis = self.require_redis_client()

        try:
            messages = await redis.xread(
                {build_user_events_stream_key(user_id): cursor},
                block=block_ms,
                count=count,
            )
        except RedisError as exc:
            raise UserEventsUnavailableError(
                "Redis is unavailable for user events."
            ) from exc

        entries: list[UserStreamEntry] = []
        for _stream_name, stream_entries in messages or []:
            for event_id, fields in stream_entries:
                event_name = fields.get(STREAM_EVENT_FIELD)
                payload = fields.get(STREAM_PAYLOAD_FIELD)
                if not event_name or payload is None:
                    continue

                notification_id = fields.get(STREAM_NOTIFICATION_ID_FIELD)
                entries.append(
                    UserStreamEntry(
                        event_id=str(event_id),
                        event_name=str(event_name),
                        notification_id=(
                            str(notification_id)
                            if notification_id is not None
                            else None
                        ),
                        envelope_json=str(payload),
                    )
                )

        return entries


__all__ = [
    "UserEventsUnavailableError",
    "UserEventsRepository",
    "build_user_events_stream_key",
]
