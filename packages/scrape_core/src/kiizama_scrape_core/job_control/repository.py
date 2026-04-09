from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime
from math import ceil
from typing import Literal, cast

from redis.exceptions import RedisError

from kiizama_scrape_core.redis import RedisClient

from .keys import (
    build_consumer_group,
    build_lease_key,
    build_queue_key,
    build_state_key,
)
from .schemas import (
    JobLeaseStatus,
    JobQueueSpec,
    JobStatus,
    JobTransientState,
    QueuedJobMessage,
    TerminalizationDecision,
    TerminalizationDecisionStatus,
)
from .scripts import (
    LEASE_RELEASE_SCRIPT,
    LEASE_RENEW_SCRIPT,
    TERMINALIZATION_CLAIM_SCRIPT,
    lease_ttl_ms,
    lease_until,
    parse_utc_datetime,
    utc_isoformat,
)

logger = logging.getLogger(__name__)
UNAVAILABLE_MESSAGE = "Redis is unavailable for job control."


class JobControlUnavailableError(RuntimeError):
    """Raised when Redis is unavailable for job orchestration."""


class JobControlRepository:
    def __init__(
        self,
        *,
        spec: JobQueueSpec,
        redis_provider: Callable[[], RedisClient],
    ) -> None:
        self.spec = spec
        self._redis_provider = redis_provider

    def require_redis_client(self) -> RedisClient:
        try:
            return self._redis_provider()
        except RuntimeError as exc:
            raise JobControlUnavailableError(str(exc)) from exc

    def assert_available(self) -> None:
        self.require_redis_client()

    async def enqueue_job(self, message: QueuedJobMessage) -> None:
        if message.execution_mode != self.spec.execution_mode:
            raise ValueError(
                "Queued job execution_mode does not match queue spec. "
                f"job_id={message.job_id} "
                f"message_mode={message.execution_mode!r} "
                f"queue_mode={self.spec.execution_mode!r}"
            )

        redis = self.require_redis_client()
        state_key = build_state_key(self.spec, message.job_id)

        try:
            await redis.hset(
                state_key,
                mapping={
                    "status": "queued",
                    "attempts": "0",
                    "updated_at": utc_isoformat(message.created_at),
                    "expires_at": (
                        utc_isoformat(message.expires_at)
                        if message.expires_at is not None
                        else ""
                    ),
                },
            )
            await self._apply_state_expiration(
                redis,
                state_key,
                expires_at=message.expires_at,
            )
            await redis.xadd(
                build_queue_key(self.spec),
                fields={
                    "job_id": message.job_id,
                    "owner_user_id": message.owner_user_id,
                    "created_at": utc_isoformat(message.created_at),
                    "expires_at": (
                        utc_isoformat(message.expires_at)
                        if message.expires_at is not None
                        else ""
                    ),
                    "execution_mode": message.execution_mode,
                    "payload": json.dumps(message.payload),
                },
                maxlen=self.spec.queue_maxlen,
            )
        except RedisError as exc:
            logger.exception("Failed to enqueue job %s in Redis.", message.job_id)
            try:
                await redis.delete(state_key)
            except RedisError:
                logger.exception(
                    "Failed to cleanup Redis state for job %s.", message.job_id
                )
            raise JobControlUnavailableError(UNAVAILABLE_MESSAGE) from exc

    async def read_new_messages(
        self,
        *,
        worker_id: str,
        count: int,
        block_ms: int,
    ) -> list[QueuedJobMessage]:
        redis = self.require_redis_client()
        try:
            response = await redis.xreadgroup(
                self._consumer_group(),
                worker_id,
                {self._queue_key(): ">"},
                count=count,
                block=block_ms,
            )
        except RedisError as exc:
            raise JobControlUnavailableError(UNAVAILABLE_MESSAGE) from exc
        return self._parse_stream_entries(response)

    async def read_reclaimed_messages(
        self,
        *,
        worker_id: str,
        min_idle_time_ms: int,
        count: int,
    ) -> list[QueuedJobMessage]:
        redis = self.require_redis_client()
        try:
            response = await redis.xautoclaim(
                self._queue_key(),
                self._consumer_group(),
                worker_id,
                min_idle_time=min_idle_time_ms,
                start_id="0-0",
                count=count,
            )
        except RedisError as exc:
            raise JobControlUnavailableError(UNAVAILABLE_MESSAGE) from exc

        if not isinstance(response, (list, tuple)) or len(response) < 2:
            return []
        return self._parse_stream_entries([(self._queue_key(), response[1])])

    async def ack_message(self, message_id: str) -> None:
        redis = self.require_redis_client()
        try:
            await redis.xack(self._queue_key(), self._consumer_group(), message_id)
            await redis.xdel(self._queue_key(), message_id)
        except RedisError as exc:
            raise JobControlUnavailableError(UNAVAILABLE_MESSAGE) from exc

    async def claim_lease(
        self,
        job_id: str,
        *,
        lease_token: str,
        lease_seconds: int,
        now: datetime,
    ) -> JobLeaseStatus:
        redis = self.require_redis_client()
        try:
            acquired = await redis.set(
                build_lease_key(self.spec, job_id),
                lease_token,
                nx=True,
                ex=lease_seconds,
            )
        except RedisError as exc:
            raise JobControlUnavailableError(UNAVAILABLE_MESSAGE) from exc

        return JobLeaseStatus(
            job_id=job_id,
            lease_token=lease_token,
            owned=bool(acquired),
            leased_until=lease_until(now, lease_seconds) if acquired else None,
        )

    async def renew_lease(
        self,
        job_id: str,
        *,
        lease_token: str,
        lease_seconds: int,
        now: datetime,
    ) -> JobLeaseStatus:
        redis = self.require_redis_client()
        leased_until_at = lease_until(now, lease_seconds)
        state_key = build_state_key(self.spec, job_id)

        try:
            renewed = await redis.eval(
                LEASE_RENEW_SCRIPT,
                1,
                build_lease_key(self.spec, job_id),
                lease_token,
                str(lease_ttl_ms(lease_seconds)),
            )
            owned = str(renewed) == "1"
            if owned:
                await redis.hset(
                    state_key,
                    mapping={
                        "heartbeat_at": utc_isoformat(now),
                        "leased_until": utc_isoformat(leased_until_at),
                        "updated_at": utc_isoformat(now),
                    },
                )
        except RedisError as exc:
            raise JobControlUnavailableError(UNAVAILABLE_MESSAGE) from exc

        return JobLeaseStatus(
            job_id=job_id,
            lease_token=lease_token,
            owned=owned,
            leased_until=leased_until_at if owned else None,
        )

    async def release_lease(
        self,
        job_id: str,
        *,
        lease_token: str,
    ) -> JobLeaseStatus:
        redis = self.require_redis_client()
        try:
            released = await redis.eval(
                LEASE_RELEASE_SCRIPT,
                1,
                build_lease_key(self.spec, job_id),
                lease_token,
            )
        except RedisError as exc:
            raise JobControlUnavailableError(UNAVAILABLE_MESSAGE) from exc

        return JobLeaseStatus(
            job_id=job_id,
            lease_token=lease_token,
            owned=bool(released),
            leased_until=None,
        )

    async def read_state(self, job_id: str) -> JobTransientState | None:
        redis = self.require_redis_client()
        try:
            raw_state = await redis.hgetall(build_state_key(self.spec, job_id))
        except RedisError as exc:
            raise JobControlUnavailableError(UNAVAILABLE_MESSAGE) from exc

        if not raw_state:
            return None
        return self._parse_state(raw_state)

    async def write_running_state(
        self,
        job_id: str,
        *,
        worker_id: str,
        lease_seconds: int,
        now: datetime,
        expires_at: datetime | None = None,
    ) -> JobTransientState:
        redis = self.require_redis_client()
        state_key = build_state_key(self.spec, job_id)
        leased_until_at = lease_until(now, lease_seconds)
        started_at = now

        try:
            attempts = await redis.hincrby(state_key, "attempts", 1)
            await redis.hsetnx(state_key, "started_at", utc_isoformat(now))
            started_at = (
                parse_utc_datetime(await redis.hget(state_key, "started_at")) or now
            )
            await redis.hset(
                state_key,
                mapping={
                    "status": "running",
                    "worker_id": worker_id,
                    "heartbeat_at": utc_isoformat(now),
                    "leased_until": utc_isoformat(leased_until_at),
                    "updated_at": utc_isoformat(now),
                    "expires_at": (
                        utc_isoformat(expires_at) if expires_at is not None else ""
                    ),
                },
            )
            await self._apply_state_expiration(
                redis,
                state_key,
                expires_at=expires_at,
                reference_time=now,
            )
        except RedisError as exc:
            raise JobControlUnavailableError(UNAVAILABLE_MESSAGE) from exc

        return JobTransientState(
            status="running",
            attempts=int(attempts),
            worker_id=worker_id,
            started_at=started_at,
            heartbeat_at=now,
            leased_until=leased_until_at,
            updated_at=now,
            expires_at=expires_at,
        )

    async def claim_terminal_state(
        self,
        job_id: str,
        *,
        status: JobStatus,
        attempt: int,
        worker_id: str,
        completed_at: datetime,
        notification_id: str,
    ) -> TerminalizationDecision:
        redis = self.require_redis_client()
        state_key = build_state_key(self.spec, job_id)

        try:
            result = await redis.eval(
                TERMINALIZATION_CLAIM_SCRIPT,
                1,
                state_key,
                status,
                str(attempt),
                worker_id,
                utc_isoformat(completed_at),
                notification_id,
            )
        except RedisError as exc:
            raise JobControlUnavailableError(UNAVAILABLE_MESSAGE) from exc

        if not isinstance(result, list) or len(result) != 7:
            raise RuntimeError("Unexpected Redis terminalization claim result.")

        decision_raw = str(result[0])
        if decision_raw not in {
            "accepted_new",
            "accepted_pending",
            "duplicate",
            "conflict",
        }:
            raise RuntimeError(
                f"Unexpected Redis terminalization decision: {decision_raw!r}."
            )

        status_raw = str(result[1])
        if status_raw not in {"done", "failed"}:
            raise RuntimeError(
                f"Unexpected Redis terminalization status: {status_raw!r}."
            )

        return TerminalizationDecision(
            decision=cast(TerminalizationDecisionStatus, decision_raw),
            status=cast(Literal["done", "failed"], status_raw),
            attempts=int(result[2]) if str(result[2]) else 0,
            worker_id=str(result[3]) if str(result[3]) else None,
            completed_at=parse_utc_datetime(result[4]),
            notification_id=str(result[5]) if str(result[5]) else None,
            terminal_event_id=str(result[6]) if str(result[6]) else None,
        )

    async def complete_terminal_state(
        self,
        job_id: str,
        *,
        terminal_event_id: str,
    ) -> JobTransientState | None:
        redis = self.require_redis_client()
        state_key = build_state_key(self.spec, job_id)
        try:
            await redis.hset(
                state_key,
                mapping={
                    "terminal_event_id": terminal_event_id,
                },
            )
            raw_state = await redis.hgetall(state_key)
        except RedisError as exc:
            raise JobControlUnavailableError(UNAVAILABLE_MESSAGE) from exc

        if not raw_state:
            return None
        return self._parse_state(raw_state)

    async def expire_state(self, job_id: str) -> None:
        redis = self.require_redis_client()
        state_key = build_state_key(self.spec, job_id)
        try:
            raw_expires_at = await redis.hget(state_key, "expires_at")
            expires_at = parse_utc_datetime(raw_expires_at)
            ttl_seconds = self.spec.state_ttl_seconds
            if expires_at is not None:
                remaining_seconds = ceil(
                    (expires_at - datetime.now(expires_at.tzinfo)).total_seconds()
                )
                if remaining_seconds <= 0:
                    await redis.delete(state_key)
                    return
                ttl_seconds = min(ttl_seconds, remaining_seconds)

            await redis.expire(state_key, ttl_seconds)
        except RedisError as exc:
            raise JobControlUnavailableError(UNAVAILABLE_MESSAGE) from exc

    def _queue_key(self) -> str:
        return build_queue_key(self.spec)

    def _consumer_group(self) -> str:
        return build_consumer_group(self.spec)

    def _parse_stream_entries(
        self,
        response: object,
    ) -> list[QueuedJobMessage]:
        messages: list[QueuedJobMessage] = []
        if not isinstance(response, list):
            return messages

        for _stream_name, entries in response:
            if not isinstance(entries, list):
                continue
            for message_id, raw_fields in entries:
                if not isinstance(raw_fields, dict):
                    continue

                created_at = parse_utc_datetime(raw_fields.get("created_at"))
                if created_at is None:
                    continue
                expires_at = parse_utc_datetime(raw_fields.get("expires_at"))

                payload_raw = raw_fields.get("payload")
                payload: dict[str, object] = {}
                if isinstance(payload_raw, str) and payload_raw:
                    try:
                        parsed_payload = json.loads(payload_raw)
                    except json.JSONDecodeError:
                        parsed_payload = {}
                    if isinstance(parsed_payload, dict):
                        payload = parsed_payload

                messages.append(
                    QueuedJobMessage(
                        message_id=str(message_id),
                        job_id=str(raw_fields.get("job_id", "")),
                        owner_user_id=str(raw_fields.get("owner_user_id", "")),
                        execution_mode=self._parse_execution_mode(raw_fields),
                        created_at=created_at,
                        expires_at=expires_at,
                        payload=dict(payload),
                    )
                )
        return messages

    def _parse_execution_mode(
        self, raw_fields: dict[str, object]
    ) -> Literal[
        "worker",
        "apify",
    ]:
        raw_execution_mode = raw_fields.get("execution_mode")
        if raw_execution_mode in {"worker", "apify"}:
            return cast(Literal["worker", "apify"], raw_execution_mode)
        return self.spec.execution_mode

    def _parse_state(self, raw_state: dict[str, object]) -> JobTransientState:
        attempts_raw = raw_state.get("attempts")
        attempts = 0
        if attempts_raw not in (None, ""):
            if not isinstance(attempts_raw, (int, str, bytes, bytearray)):
                raise RuntimeError(
                    f"Unexpected Redis attempts value: {attempts_raw!r}."
                )
            attempts = int(attempts_raw)
        error = raw_state.get("error")
        status_raw = str(raw_state.get("status", "queued"))

        if status_raw not in {"queued", "running", "done", "failed"}:
            raise RuntimeError(f"Unexpected Redis job status: {status_raw!r}.")

        return JobTransientState(
            status=cast(JobStatus, status_raw),
            attempts=attempts,
            worker_id=(
                str(raw_state["worker_id"]) if raw_state.get("worker_id") else None
            ),
            started_at=parse_utc_datetime(raw_state.get("started_at")),
            heartbeat_at=parse_utc_datetime(raw_state.get("heartbeat_at")),
            leased_until=parse_utc_datetime(raw_state.get("leased_until")),
            updated_at=parse_utc_datetime(raw_state.get("updated_at")),
            completed_at=parse_utc_datetime(raw_state.get("completed_at")),
            expires_at=parse_utc_datetime(raw_state.get("expires_at")),
            error=str(error) if error else None,
            notification_id=(
                str(raw_state["notification_id"])
                if raw_state.get("notification_id")
                else None
            ),
            terminal_event_id=(
                str(raw_state["terminal_event_id"])
                if raw_state.get("terminal_event_id")
                else None
            ),
        )

    async def _apply_state_expiration(
        self,
        redis: RedisClient,
        state_key: str,
        *,
        expires_at: datetime | None,
        reference_time: datetime | None = None,
    ) -> None:
        if expires_at is None:
            return

        now = reference_time or datetime.now(expires_at.tzinfo)
        remaining_seconds = ceil((expires_at - now).total_seconds())
        if remaining_seconds <= 0:
            await redis.delete(state_key)
            return

        await redis.expire(state_key, remaining_seconds)


__all__ = ["JobControlRepository", "JobControlUnavailableError"]
