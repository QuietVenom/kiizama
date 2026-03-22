from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime

from redis.exceptions import ResponseError

from .keys import build_consumer_group, build_queue_key
from .repository import JobControlRepository
from .schemas import QueuedJobMessage
from .scripts import now_utc

TERMINAL_JOB_STATUSES = {"done", "failed"}

logger = logging.getLogger(__name__)


def _is_expired(expires_at: datetime | None, *, reference_time: datetime) -> bool:
    return expires_at is not None and reference_time >= expires_at


@dataclass(slots=True)
class JobRuntimeHandle:
    message: QueuedJobMessage
    attempt: int
    lease_token: str
    started_at: datetime
    lease_lost: asyncio.Event
    heartbeat_task: asyncio.Task[None] | None = None

    @property
    def job_id(self) -> str:
        return self.message.job_id


class JobWorkerRuntime:
    def __init__(
        self,
        *,
        repository: JobControlRepository,
        worker_id: str,
        lease_seconds: int,
        heartbeat_seconds: float,
        poll_seconds: float,
        reclaimed_message_count: int = 10,
        new_message_count: int = 1,
    ) -> None:
        self._repository = repository
        self._spec = repository.spec
        self._worker_id = worker_id
        self._lease_seconds = lease_seconds
        self._heartbeat_seconds = heartbeat_seconds
        self._poll_seconds = poll_seconds
        self._reclaimed_message_count = reclaimed_message_count
        self._new_message_count = new_message_count

    async def ensure_consumer_group(self) -> None:
        redis = self._repository.require_redis_client()
        try:
            await redis.xgroup_create(
                build_queue_key(self._spec),
                build_consumer_group(self._spec),
                id="0",
                mkstream=True,
            )
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def poll_messages(self) -> list[QueuedJobMessage]:
        reclaimed_messages = await self._repository.read_reclaimed_messages(
            worker_id=self._worker_id,
            min_idle_time_ms=self.lease_ttl_ms(),
            count=self._reclaimed_message_count,
        )
        if reclaimed_messages:
            return reclaimed_messages

        return await self._repository.read_new_messages(
            worker_id=self._worker_id,
            count=self._new_message_count,
            block_ms=max(1, int(self._poll_seconds * 1000)),
        )

    async def start_job(self, message: QueuedJobMessage) -> JobRuntimeHandle | None:
        state = await self._repository.read_state(message.job_id)
        if state is not None and state.status in TERMINAL_JOB_STATUSES:
            await self._ack(message)
            return None

        expires_at = message.expires_at or (
            state.expires_at if state is not None else None
        )
        if _is_expired(expires_at, reference_time=now_utc()):
            logger.info(
                "Discarding expired scrape job %s before execution.", message.job_id
            )
            await self._repository.expire_state(message.job_id)
            await self._ack(message)
            return None

        started_at = now_utc()
        lease_token = self._worker_id
        lease_status = await self._repository.claim_lease(
            message.job_id,
            lease_token=lease_token,
            lease_seconds=self._lease_seconds,
            now=started_at,
        )
        if not lease_status.owned:
            return None

        try:
            running_state = await self._repository.write_running_state(
                message.job_id,
                worker_id=self._worker_id,
                lease_seconds=self._lease_seconds,
                now=started_at,
                expires_at=expires_at,
            )
        except Exception:
            await self._repository.release_lease(
                message.job_id,
                lease_token=lease_token,
            )
            raise
        handle = JobRuntimeHandle(
            message=message,
            attempt=running_state.attempts,
            lease_token=lease_token,
            started_at=started_at,
            lease_lost=asyncio.Event(),
        )
        handle.heartbeat_task = asyncio.create_task(self._maintain_heartbeat(handle))
        return handle

    async def finish_job(
        self,
        handle: JobRuntimeHandle,
        *,
        ack: bool,
        expire_state: bool = False,
    ) -> None:
        if handle.heartbeat_task is not None:
            handle.heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await handle.heartbeat_task

        try:
            if ack:
                await self._ack(handle.message)
        finally:
            await self._repository.release_lease(
                handle.job_id,
                lease_token=handle.lease_token,
            )
            if expire_state:
                await self._repository.expire_state(handle.job_id)

    def lease_ttl_ms(self) -> int:
        return self._lease_seconds * 1000

    async def _ack(self, message: QueuedJobMessage) -> None:
        if message.message_id is None:
            raise ValueError("Queued job message is missing message_id.")
        await self._repository.ack_message(message.message_id)

    async def _maintain_heartbeat(self, handle: JobRuntimeHandle) -> None:
        try:
            while not handle.lease_lost.is_set():
                await asyncio.sleep(self._heartbeat_seconds)
                if handle.lease_lost.is_set():
                    return

                renewed = await self._repository.renew_lease(
                    handle.job_id,
                    lease_token=handle.lease_token,
                    lease_seconds=self._lease_seconds,
                    now=now_utc(),
                )
                if renewed.owned:
                    continue

                logger.warning("Lease lost for job %s.", handle.job_id)
                handle.lease_lost.set()
                return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Heartbeat failed for job %s: %s", handle.job_id, exc)
            handle.lease_lost.set()


__all__ = ["JobRuntimeHandle", "JobWorkerRuntime", "TERMINAL_JOB_STATUSES"]
