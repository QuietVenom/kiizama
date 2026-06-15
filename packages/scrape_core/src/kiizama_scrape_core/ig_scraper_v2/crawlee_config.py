from __future__ import annotations

from datetime import timedelta
from typing import Any

from crawlee import ConcurrencySettings
from crawlee.proxy_configuration import ProxyConfiguration

from .config import ProxyConfig, ScraperV2Config
from .stealth import merge_extra_headers


def build_proxy_configuration(config: ProxyConfig) -> ProxyConfiguration | None:
    if not config.use_isp_proxy:
        return None
    return ProxyConfiguration(proxy_urls=list(config.proxy_urls))


def build_playwright_crawler_kwargs(
    config: ScraperV2Config,
    *,
    storage_state: dict[str, Any] | None = None,
    extra_http_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    proxy_configuration = build_proxy_configuration(config.proxy)
    browser_new_context_options: dict[str, Any] = {
        "locale": config.browser.locale,
        "user_agent": config.browser.user_agent,
        "viewport": {
            "width": config.browser.viewport_width,
            "height": config.browser.viewport_height,
        },
        "extra_http_headers": merge_extra_headers(
            locale=config.browser.locale,
            extra_headers=extra_http_headers,
        ),
    }
    if storage_state:
        browser_new_context_options["storage_state"] = storage_state

    return {
        "headless": config.browser.headless,
        "navigation_timeout": timedelta(milliseconds=config.browser.timeout_ms),
        "browser_new_context_options": browser_new_context_options,
        "concurrency_settings": ConcurrencySettings(
            min_concurrency=1,
            desired_concurrency=config.crawler.max_concurrent,
            max_concurrency=config.crawler.max_concurrent,
        ),
        "max_request_retries": config.crawler.max_request_retries,
        "proxy_configuration": proxy_configuration,
        "use_session_pool": config.crawler.use_session_pool,
    }


__all__ = [
    "build_playwright_crawler_kwargs",
    "build_proxy_configuration",
]
