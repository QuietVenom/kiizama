from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from fastapi import Request
from fastapi.sse import ServerSentEvent
from pydantic import ValidationError
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.resilience import (
    mark_dependency_failure,
    mark_dependency_success,
    translate_redis_exception,
)

from .repository import (
    UserEventsRepository,
    UserEventsUnavailableError,
    get_user_events_repository,
)
from .schemas import UserEventEnvelope

logger = logging.getLogger(__name__)
SSE_DEGRADED_RETRY_MS = 30_000


class UserEventStreamService:
    def __init__(
        self,
        *,
        repository: UserEventsRepository | None = None,
        read_block_ms: int | None = None,
    ) -> None:
        self._repository = repository or get_user_events_repository()
        self._read_block_ms = read_block_ms or settings.USER_EVENTS_SSE_READ_BLOCK_MS

    def assert_available(self) -> None:
        self._repository.assert_available()

    async def assert_connection_available(self) -> None:
        try:
            redis = self._repository.require_redis_client()
            await asyncio.wait_for(redis.ping(), timeout=1.0)
        except (
            UserEventsUnavailableError,
            RedisError,
            RuntimeError,
            TimeoutError,
        ) as exc:
            translated = translate_redis_exception(
                exc,
                detail="Redis is unavailable for user events.",
            )
            mark_dependency_failure(
                "redis",
                context="user-event-sse-connect",
                detail=translated.detail,
                status="degraded",
                exc=exc,
            )
            raise translated from exc
        else:
            mark_dependency_success(
                "redis",
                context="user-event-sse-connect",
                detail="Redis is healthy for user events.",
            )

    def stream_events(
        self,
        request: Request,
        *,
        user_id: str,
        last_event_id: str | None,
    ) -> AsyncIterator[ServerSentEvent]:
        self.assert_available()
        return self._event_generator(
            request,
            user_id=user_id,
            last_event_id=last_event_id,
        )

    async def _event_generator(
        self,
        request: Request,
        *,
        user_id: str,
        last_event_id: str | None,
    ) -> AsyncIterator[ServerSentEvent]:
        cursor = self.normalize_cursor(last_event_id)

        try:
            while True:
                if await request.is_disconnected():
                    return

                entries = await self._repository.read_events(
                    user_id=user_id,
                    cursor=cursor,
                    block_ms=self._read_block_ms,
                    count=10,
                )
                for entry in entries:
                    cursor = entry.event_id
                    envelope = self._parse_envelope(entry.envelope_json)
                    if envelope is None:
                        continue
                    yield ServerSentEvent(
                        id=entry.event_id,
                        event=entry.event_name,
                        data=envelope.model_dump(mode="json"),
                    )
        except asyncio.CancelledError:
            raise
        except UserEventsUnavailableError as exc:
            translated = translate_redis_exception(
                exc,
                detail="Redis is unavailable for user events.",
            )
            mark_dependency_failure(
                "redis",
                context="user-event-sse-stream",
                detail=translated.detail,
                status="degraded",
                exc=exc,
            )
            yield ServerSentEvent(retry=SSE_DEGRADED_RETRY_MS)
            return
        except Exception:
            logger.exception("User event SSE stream failed for user %s.", user_id)

    @staticmethod
    def normalize_cursor(last_event_id: str | None) -> str:
        return last_event_id or "$"

    @staticmethod
    def _parse_envelope(payload_raw: str) -> UserEventEnvelope | None:
        try:
            return UserEventEnvelope.model_validate_json(payload_raw)
        except ValidationError:
            return None


def get_user_event_stream_service() -> UserEventStreamService:
    return UserEventStreamService()


__all__ = [
    "UserEventsUnavailableError",
    "UserEventStreamService",
    "get_user_event_stream_service",
]
