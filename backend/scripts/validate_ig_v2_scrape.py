from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from typing import Any

from kiizama_scrape_core.ig_scraper_v2 import (
    InstagramBatchScrapeRunner,
    InstagramBatchScrapeRunResult,
    build_scraper_v2_config,
)
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine, ping_postgres
from app.features.ig_scraper_v2_runtime import BackendInstagramCredentialsStoreV2
from scripts.validate_ig_v2_login import FilteredInstagramCredentialsStore

EXIT_SUCCESS = 0
EXIT_SCRAPE_FAILED = 1
EXIT_CONFIG_ERROR = 2
EXIT_INTERRUPTED = 130


@dataclass(frozen=True, slots=True)
class ScriptOptions:
    usernames: tuple[str, ...]
    headless: bool | None
    use_proxy: bool
    proxy_urls: tuple[str, ...] | None
    timeout_ms: int | None
    credential_id: str | None
    login_username: str | None
    max_concurrent: int | None
    max_posts: int
    json_output: bool


@dataclass(frozen=True, slots=True)
class SafeBatchScrapeOutput:
    success: bool
    credential_id: str | None
    session_message: str
    error: str | None
    proxy_mode: str
    headless: bool
    counters: dict[str, int]
    results: dict[str, dict[str, Any]]


def parse_args(argv: list[str] | None = None) -> ScriptOptions:
    parser = argparse.ArgumentParser(
        description="Run Instagram scraper v2 snapshot scraping against backend DB."
    )
    parser.add_argument(
        "usernames",
        nargs="+",
        help="Instagram usernames to scrape.",
    )
    headless_group = parser.add_mutually_exclusive_group()
    headless_group.add_argument(
        "--headed",
        action="store_true",
        help="Run Chromium in headed mode.",
    )
    headless_group.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium in headless mode.",
    )
    parser.add_argument(
        "--use-proxy",
        action="store_true",
        help="Enable ISP/DECODO proxy mode.",
    )
    parser.add_argument(
        "--proxy-url",
        action="append",
        default=None,
        help="Proxy URL for DECODO/ISP mode. Can be passed multiple times.",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=None,
        help="Playwright navigation timeout in milliseconds.",
    )
    parser.add_argument(
        "--credential-id",
        default=None,
        help="Scrape with a specific private.ig_credentials id.",
    )
    parser.add_argument(
        "--login-username",
        default=None,
        help="Scrape with a specific Instagram login username.",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=None,
        help="Maximum concurrent profile pages.",
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=12,
        help="Maximum posts and reels to collect per profile.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON to stdout.",
    )

    args = parser.parse_args(argv)
    headless: bool | None = None
    if args.headed:
        headless = False
    elif args.headless:
        headless = True

    proxy_urls = tuple(args.proxy_url) if args.proxy_url else None
    return ScriptOptions(
        usernames=tuple(args.usernames),
        headless=headless,
        use_proxy=args.use_proxy,
        proxy_urls=proxy_urls,
        timeout_ms=args.timeout_ms,
        credential_id=args.credential_id,
        login_username=args.login_username,
        max_concurrent=args.max_concurrent,
        max_posts=args.max_posts,
        json_output=args.json,
    )


def configure_secret_from_settings() -> None:
    os.environ.setdefault(
        "SECRET_KEY_IG_CREDENTIALS",
        settings.SECRET_KEY_IG_CREDENTIALS,
    )


def build_config_from_options(options: ScriptOptions):
    return build_scraper_v2_config(
        headless=options.headless,
        timeout_ms=options.timeout_ms,
        max_concurrent=options.max_concurrent,
        use_isp_proxy=options.use_proxy,
        proxy_urls=options.proxy_urls,
    )


def build_credentials_store(options: ScriptOptions):
    base_store = BackendInstagramCredentialsStoreV2(lambda: Session(engine))
    return FilteredInstagramCredentialsStore(
        base_store,
        credential_id=options.credential_id,
        login_username=options.login_username,
    )


def build_safe_output(
    result: InstagramBatchScrapeRunResult,
    *,
    proxy_mode: str,
    headless: bool,
) -> SafeBatchScrapeOutput:
    return SafeBatchScrapeOutput(
        success=result.success,
        credential_id=result.credential_id,
        session_message=result.session_message,
        error=result.error,
        proxy_mode=proxy_mode,
        headless=headless,
        counters=asdict(result.counters),
        results=result.results,
    )


def print_output(
    output: SafeBatchScrapeOutput,
    *,
    json_output: bool,
) -> None:
    payload = asdict(output)
    if json_output:
        sys.stdout.write(f"{json.dumps(payload, sort_keys=True)}\n")
        return

    sys.stdout.write(f"success: {output.success}\n")
    sys.stdout.write(f"credential_id: {output.credential_id}\n")
    sys.stdout.write(f"session_message: {output.session_message}\n")
    sys.stdout.write(f"error: {output.error}\n")
    sys.stdout.write(f"proxy_mode: {output.proxy_mode}\n")
    sys.stdout.write(f"headless: {output.headless}\n")
    sys.stdout.write(f"counters: {output.counters}\n")
    for username, profile_result in output.results.items():
        user = profile_result.get("user")
        user_data = user if isinstance(user, dict) else {}
        sys.stdout.write(
            "profile: "
            f"{username} "
            f"success={profile_result.get('success')} "
            f"matched={user_data.get('username')} "
            f"posts={len(profile_result.get('posts') or [])} "
            f"reels={len(profile_result.get('reels') or [])} "
            f"error={profile_result.get('error')}\n"
        )


async def run_validation(options: ScriptOptions) -> SafeBatchScrapeOutput:
    configure_secret_from_settings()
    ping_postgres()
    config = build_config_from_options(options)
    store = build_credentials_store(options)
    result = await InstagramBatchScrapeRunner(
        config=config,
        credentials_store=store,
        usernames=list(options.usernames),
        max_posts=options.max_posts,
    ).run()
    return build_safe_output(
        result,
        proxy_mode="decodo" if config.proxy.use_isp_proxy else "local",
        headless=config.browser.headless,
    )


def _is_config_error(exc: Exception) -> bool:
    return isinstance(exc, (ValueError, ValidationError, SQLAlchemyError, RuntimeError))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    try:
        options = parse_args(argv)
        output = asyncio.run(run_validation(options))
        print_output(output, json_output=options.json_output)
        return EXIT_SUCCESS if output.success else EXIT_SCRAPE_FAILED
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED
    except SystemExit:
        raise
    except Exception as exc:
        if _is_config_error(exc):
            json_output = "--json" in (argv if argv is not None else sys.argv[1:])
            output = SafeBatchScrapeOutput(
                success=False,
                credential_id=None,
                session_message="Configuration or dependency error",
                error=str(exc),
                proxy_mode="unknown",
                headless=True,
                counters={
                    "requested": 0,
                    "successful": 0,
                    "failed": 0,
                    "not_found": 0,
                },
                results={},
            )
            print_output(output, json_output=json_output)
            return EXIT_CONFIG_ERROR
        raise


if __name__ == "__main__":
    raise SystemExit(main())
