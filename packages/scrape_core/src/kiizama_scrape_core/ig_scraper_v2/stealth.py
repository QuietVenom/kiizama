from __future__ import annotations

import logging

from playwright.async_api import Page

STEALTH_JS = r"""
(() => {
    Object.defineProperty(navigator, 'plugins', {
        get: () => [{
            name: 'Chrome PDF Plugin',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format',
            length: 1,
        }, {
            name: 'Chrome PDF Viewer',
            filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
            description: 'Portable Document Format',
            length: 1,
        }, {
            name: 'Native Client',
            filename: 'internal-nacl-plugin',
            description: 'Native Client Executable',
            length: 1,
        }],
    });

    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
    });

    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
    });

    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters)
    );

    window.chrome = {
        runtime: {},
    };
})();
"""


def build_stealth_headers(locale: str) -> dict[str, str]:
    language = locale.strip() or "en-US"
    return {
        "Accept-Language": f"{language},{language.split('-')[0]};q=0.9,en;q=0.8",
        "Sec-Ch-Ua": '"Chromium";v="139", "Google Chrome";v="139", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
    }


async def add_stealth(
    page: Page,
    *,
    locale: str,
    logger: logging.Logger | None = None,
) -> None:
    try:
        await page.add_init_script(STEALTH_JS)
        await page.set_extra_http_headers(build_stealth_headers(locale))
    except Exception as exc:
        active_logger = logger or logging.getLogger(
            "kiizama_scrape_core.ig_scraper_v2.stealth"
        )
        active_logger.warning("Failed to add stealth script: %s", exc)


def merge_extra_headers(
    *,
    locale: str,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, str]:
    headers: dict[str, str] = build_stealth_headers(locale)
    for key, value in (extra_headers or {}).items():
        if key.lower() in {"cookie", "user-agent"}:
            continue
        headers[str(key)] = str(value)
    return headers


__all__ = [
    "STEALTH_JS",
    "add_stealth",
    "build_stealth_headers",
    "merge_extra_headers",
]
