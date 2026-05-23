from __future__ import annotations

from typing import Any

import pytest
from kiizama_scrape_core.ig_scraper_v2 import (
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeResponse,
    InstagramScraperV2Backend,
    build_scraper_v2_config,
)
from kiizama_scrape_core.ig_scraper_v2.classes import CredentialCandidate


class FakeCredentialsStore:
    async def list_credentials(self, *, limit: int) -> list[CredentialCandidate]:
        del limit
        return []

    def decrypt_password(self, encrypted_password: str) -> str:
        return encrypted_password

    async def persist_session(
        self,
        credential_id: str,
        state: dict[str, Any],
    ) -> bool:
        del credential_id, state
        return True


class FakeRunner:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    async def run_response(self) -> InstagramBatchScrapeResponse:
        return InstagramBatchScrapeResponse()


@pytest.mark.anyio
async def test_v2_backend_uses_runtime_config_for_runner() -> None:
    calls: list[dict[str, Any]] = []

    def fake_runner_factory(**kwargs: Any) -> FakeRunner:
        calls.append(kwargs)
        return FakeRunner(**kwargs)

    backend = InstagramScraperV2Backend(
        config=build_scraper_v2_config(
            env={
                "IG_SCRAPER_V2_USE_ISP_PROXY": "true",
                "IG_SCRAPER_V2_ISP_PROXY_URLS": "http://env-proxy.example:8000",
                "IG_SCRAPER_V2_HEADLESS": "true",
                "IG_SCRAPER_V2_TIMEOUT_MS": "30000",
                "IG_SCRAPER_V2_MAX_CONCURRENT": "1",
                "IG_SCRAPER_V2_MAX_POSTS": "7",
            }
        ),
        credentials_store=FakeCredentialsStore(),
        batch_runner_factory=fake_runner_factory,
    )
    request = InstagramBatchScrapeRequest(usernames=["Alpha"])

    await backend.scrape(request)

    runner_config = calls[0]["config"]
    assert calls[0]["usernames"] == ["alpha"]
    assert calls[0]["max_posts"] == 7
    assert runner_config.browser.headless is True
    assert runner_config.browser.timeout_ms == 30_000
    assert runner_config.browser.locale == "en-US"
    assert runner_config.crawler.max_concurrent == 1
    assert runner_config.proxy.use_isp_proxy is True
    assert runner_config.proxy.proxy_urls == ("http://env-proxy.example:8000",)
