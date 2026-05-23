from __future__ import annotations

import pytest
from crawlee.proxy_configuration import ProxyConfiguration
from kiizama_scrape_core.ig_scraper_v2 import (
    build_proxy_configuration,
    build_scraper_v2_config,
)
from kiizama_scrape_core.ig_scraper_v2.constants import DEFAULT_USER_AGENT


def test_build_scraper_v2_config_without_env_uses_defaults() -> None:
    config = build_scraper_v2_config(env={})

    assert config.browser.headless is True
    assert config.browser.timeout_ms == 30_000
    assert config.browser.user_agent == DEFAULT_USER_AGENT
    assert config.browser.locale == "en-US"
    assert config.browser.viewport_width == 1920
    assert config.browser.viewport_height == 1080
    assert config.crawler.max_concurrent == 2
    assert config.max_posts == 12
    assert config.crawler.max_request_retries == 3
    assert config.crawler.use_session_pool is True
    assert config.proxy.use_isp_proxy is False
    assert config.proxy.proxy_urls == ()
    assert config.pacing.enabled is True
    assert config.pacing.min_delay_seconds == 1.0
    assert config.pacing.max_delay_seconds == 3.0
    assert config.pacing.warmup_min_seconds == 1.5
    assert config.pacing.warmup_max_seconds == 4.0


def test_build_scraper_v2_config_parses_env_values() -> None:
    config = build_scraper_v2_config(
        env={
            "IG_SCRAPER_V2_USE_ISP_PROXY": "yes",
            "IG_SCRAPER_V2_ISP_PROXY_URLS": (
                " http://proxy-one.example:8000, http://proxy-two.example:8000 "
            ),
            "IG_SCRAPER_V2_MAX_CONCURRENT": "4",
            "IG_SCRAPER_V2_HEADLESS": "false",
            "IG_SCRAPER_V2_TIMEOUT_MS": "45000",
            "IG_SCRAPER_V2_MAX_POSTS": "9",
            "IG_SCRAPER_V2_LOCALE": "es-MX",
            "IG_SCRAPER_V2_PACING_ENABLED": "on",
            "IG_SCRAPER_V2_PACING_MIN_SECONDS": "2.5",
            "IG_SCRAPER_V2_PACING_MAX_SECONDS": "6.0",
            "IG_SCRAPER_V2_WARMUP_MIN_SECONDS": "8.5",
            "IG_SCRAPER_V2_WARMUP_MAX_SECONDS": "12.0",
        }
    )

    assert config.browser.headless is False
    assert config.browser.timeout_ms == 45_000
    assert config.browser.locale == "es-MX"
    assert config.crawler.max_concurrent == 4
    assert config.max_posts == 9
    assert config.proxy.use_isp_proxy is True
    assert config.proxy.proxy_urls == (
        "http://proxy-one.example:8000",
        "http://proxy-two.example:8000",
    )
    assert config.pacing.enabled is True
    assert config.pacing.min_delay_seconds == 2.5
    assert config.pacing.max_delay_seconds == 6.0
    assert config.pacing.warmup_min_seconds == 8.5
    assert config.pacing.warmup_max_seconds == 12.0


def test_build_scraper_v2_config_rejects_isp_proxy_without_urls() -> None:
    with pytest.raises(ValueError, match="At least one proxy URL"):
        build_scraper_v2_config(
            env={
                "IG_SCRAPER_V2_USE_ISP_PROXY": "true",
                "IG_SCRAPER_V2_ISP_PROXY_URLS": "",
            }
        )


def test_build_scraper_v2_config_production_forces_isp_proxy() -> None:
    config = build_scraper_v2_config(
        env={
            "ENVIRONMENT": "production",
            "IG_SCRAPER_V2_USE_ISP_PROXY": "false",
            "IG_SCRAPER_V2_ISP_PROXY_URLS": "http://proxy.example:8000",
        }
    )

    assert config.proxy.use_isp_proxy is True
    assert config.proxy.proxy_urls == ("http://proxy.example:8000",)
    assert config.pacing.warmup_min_seconds == 8.0
    assert config.pacing.warmup_max_seconds == 20.0


def test_build_scraper_v2_config_production_rejects_missing_proxy_urls() -> None:
    with pytest.raises(ValueError, match="At least one proxy URL"):
        build_scraper_v2_config(
            env={
                "ENVIRONMENT": "production",
                "IG_SCRAPER_V2_USE_ISP_PROXY": "false",
                "IG_SCRAPER_V2_ISP_PROXY_URLS": "",
            }
        )


def test_build_scraper_v2_config_uses_isp_proxy_warmup_defaults() -> None:
    config = build_scraper_v2_config(
        env={
            "IG_SCRAPER_V2_USE_ISP_PROXY": "true",
            "IG_SCRAPER_V2_ISP_PROXY_URLS": "http://proxy.example:8000",
        }
    )

    assert config.pacing.warmup_min_seconds == 8.0
    assert config.pacing.warmup_max_seconds == 20.0


def test_build_scraper_v2_config_rejects_invalid_warmup_range() -> None:
    with pytest.raises(ValueError, match="warmup_min_seconds"):
        build_scraper_v2_config(
            env={
                "IG_SCRAPER_V2_WARMUP_MIN_SECONDS": "5.0",
                "IG_SCRAPER_V2_WARMUP_MAX_SECONDS": "2.0",
            }
        )


def test_build_scraper_v2_config_applies_explicit_overrides_after_env() -> None:
    config = build_scraper_v2_config(
        env={
            "IG_SCRAPER_V2_USE_ISP_PROXY": "true",
            "IG_SCRAPER_V2_ISP_PROXY_URLS": "http://env-proxy.example:8000",
            "IG_SCRAPER_V2_MAX_CONCURRENT": "8",
            "IG_SCRAPER_V2_HEADLESS": "false",
            "IG_SCRAPER_V2_TIMEOUT_MS": "45000",
            "IG_SCRAPER_V2_PACING_ENABLED": "true",
        },
        headless=True,
        timeout_ms=20_000,
        max_concurrent=2,
        max_posts=5,
        use_isp_proxy=False,
        proxy_urls=(),
        pacing_enabled=False,
    )

    assert config.browser.headless is True
    assert config.browser.timeout_ms == 20_000
    assert config.crawler.max_concurrent == 2
    assert config.max_posts == 5
    assert config.proxy.use_isp_proxy is False
    assert config.proxy.proxy_urls == ()
    assert config.pacing.enabled is False


def test_build_proxy_configuration_returns_none_for_local_mode() -> None:
    config = build_scraper_v2_config(env={})

    assert build_proxy_configuration(config.proxy) is None


def test_build_proxy_configuration_returns_crawlee_proxy_configuration() -> None:
    config = build_scraper_v2_config(
        env={
            "IG_SCRAPER_V2_USE_ISP_PROXY": "true",
            "IG_SCRAPER_V2_ISP_PROXY_URLS": "http://proxy.example:8000",
        }
    )

    proxy_configuration = build_proxy_configuration(config.proxy)

    assert isinstance(proxy_configuration, ProxyConfiguration)
