from __future__ import annotations

import logging
import random

import pytest
from kiizama_scrape_core.ig_scraper_v2.browser import InstagramBrowserSession
from kiizama_scrape_core.ig_scraper_v2.config import build_scraper_v2_config


def test_browser_session_uses_local_ip_by_default() -> None:
    config = build_scraper_v2_config(env={})
    session = InstagramBrowserSession(config=config)

    launch_options = session.build_launch_options()

    assert "proxy" not in launch_options


def test_browser_session_uses_decodo_proxy_when_enabled() -> None:
    config = build_scraper_v2_config(
        env={
            "IG_SCRAPER_V2_USE_ISP_PROXY": "true",
            "IG_SCRAPER_V2_ISP_PROXY_URLS": "http://proxy.example:8000",
        }
    )
    session = InstagramBrowserSession(config=config)

    launch_options = session.build_launch_options()

    assert launch_options["proxy"] == {"server": "http://proxy.example:8000"}


def test_browser_session_context_options_include_storage_state_and_headers() -> None:
    storage_state = {"cookies": [], "origins": []}
    config = build_scraper_v2_config(env={})
    session = InstagramBrowserSession(
        config=config,
        storage_state=storage_state,
        extra_http_headers={
            "X-IG-App-ID": "test-app",
            "Cookie": "ignored",
            "User-Agent": "ignored",
        },
    )

    options = session.build_context_options()

    assert options["storage_state"] == storage_state
    assert options["extra_http_headers"]["X-IG-App-ID"] == "test-app"
    assert "Cookie" not in options["extra_http_headers"]
    assert "User-Agent" not in options["extra_http_headers"]


@pytest.mark.anyio
async def test_browser_session_cold_warmup_uses_variable_delay_before_navigation() -> (
    None
):
    sleeps: list[float] = []

    async def sleeper(delay: float) -> None:
        sleeps.append(delay)

    config = build_scraper_v2_config(
        env={
            "IG_SCRAPER_V2_WARMUP_MIN_SECONDS": "3.0",
            "IG_SCRAPER_V2_WARMUP_MAX_SECONDS": "3.0",
        }
    )
    session = InstagramBrowserSession(
        config=config,
        sleeper=sleeper,
        rng=random.Random(1),
    )

    delay = await session.cold_warm_up(credential_id="cred_1")

    assert delay == 3.0
    assert sleeps == [3.0]
    assert session.timings.cold_warmup_seconds == 3.0


@pytest.mark.anyio
async def test_browser_session_cold_warmup_redacts_credential_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def sleeper(_delay: float) -> None:
        return None

    caplog.set_level(
        logging.INFO,
        logger="kiizama_scrape_core.ig_scraper_v2.browser",
    )
    config = build_scraper_v2_config(
        env={
            "IG_SCRAPER_V2_WARMUP_MIN_SECONDS": "1.0",
            "IG_SCRAPER_V2_WARMUP_MAX_SECONDS": "1.0",
        }
    )
    session = InstagramBrowserSession(
        config=config,
        sleeper=sleeper,
        rng=random.Random(1),
    )

    await session.cold_warm_up(credential_id="019e5cc6-d98a-71f6-975d-bd164c313865")

    assert "019e5cc6-...-bd164c313865" in caplog.text
    assert "019e5cc6-d98a-71f6-975d-bd164c313865" not in caplog.text
