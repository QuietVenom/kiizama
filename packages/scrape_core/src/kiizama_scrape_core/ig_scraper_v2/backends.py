from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

from .batch_runner import InstagramBatchScrapeRunner
from .config import ScraperV2Config
from .ports import InstagramCredentialsStore
from .schemas import InstagramBatchScrapeRequest, InstagramBatchScrapeResponse


class BatchRunner(Protocol):
    async def run_response(self) -> InstagramBatchScrapeResponse: ...


BatchRunnerFactory = Callable[..., BatchRunner]


class InstagramScraperV2Backend:
    def __init__(
        self,
        *,
        config: ScraperV2Config,
        credentials_store: InstagramCredentialsStore,
        logger: logging.Logger | None = None,
        batch_runner_factory: BatchRunnerFactory = InstagramBatchScrapeRunner,
        job_id: str | None = None,
    ) -> None:
        self.config = config
        self.credentials_store = credentials_store
        self.logger = logger
        self.batch_runner_factory = batch_runner_factory
        self.job_id = job_id

    async def scrape(
        self,
        request: InstagramBatchScrapeRequest,
    ) -> InstagramBatchScrapeResponse:
        runner = self.batch_runner_factory(
            config=self.config,
            credentials_store=self.credentials_store,
            usernames=request.usernames,
            max_posts=self.config.max_posts,
            logger=self.logger,
            job_id=self.job_id,
        )
        return await runner.run_response()


__all__ = ["InstagramScraperV2Backend"]
