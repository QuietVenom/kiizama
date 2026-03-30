from __future__ import annotations

from typing import Protocol

from kiizama_scrape_core.ig_scraper.schemas import (
    InstagramScrapeJobTerminalizationRequest,
)
from kiizama_scrape_core.job_control import JobRuntimeHandle, QueuedJobMessage

from scrape_worker.backend_client import WorkerBackendCompletionResult


class WorkerRuntimePort(Protocol):
    async def ensure_consumer_group(self) -> None: ...

    async def poll_messages(self) -> list[QueuedJobMessage]: ...

    async def start_job(self, message: QueuedJobMessage) -> JobRuntimeHandle | None: ...

    async def finish_job(
        self,
        handle: JobRuntimeHandle,
        *,
        ack: bool,
        expire_state: bool = False,
    ) -> None: ...


class BackendCompletionPort(Protocol):
    async def complete_job(
        self,
        *,
        job_id: str,
        payload: InstagramScrapeJobTerminalizationRequest,
    ) -> WorkerBackendCompletionResult: ...


__all__ = [
    "BackendCompletionPort",
    "WorkerRuntimePort",
]
