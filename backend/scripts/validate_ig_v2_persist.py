from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass

from kiizama_scrape_core.ig_scraper_v2 import (
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeRunner,
    build_batch_scrape_summary,
    build_scraper_v2_config,
    enrich_with_ai_analysis,
    persist_scrape_results_to_db,
    prepare_scrape_batch_payload,
)
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine, ping_postgres
from app.features.ig_scraper_v2_runtime import (
    BackendInstagramCredentialsStoreV2,
    BackendInstagramProfileAnalysisServiceV2,
    BackendInstagramScrapePersistenceV2,
)
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
    skip_ai: bool
    json_output: bool


@dataclass(frozen=True, slots=True)
class SafePersistOutput:
    success: bool
    error: str | None
    proxy_mode: str
    headless: bool
    counters: dict[str, int]
    summary: dict
    persisted_usernames: list[str]
    skipped_usernames: list[str]
    not_found_usernames: list[str]
    failed_usernames: list[str]


def parse_args(argv: list[str] | None = None) -> ScriptOptions:
    parser = argparse.ArgumentParser(
        description="Run Instagram scraper v2 and persist results to the backend DB."
    )
    parser.add_argument("usernames", nargs="+", help="Instagram usernames to scrape.")
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
        "--skip-ai",
        action="store_true",
        help="Skip AI enrichment while validating persistence.",
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

    return ScriptOptions(
        usernames=tuple(args.usernames),
        headless=headless,
        use_proxy=args.use_proxy,
        proxy_urls=tuple(args.proxy_url) if args.proxy_url else None,
        timeout_ms=args.timeout_ms,
        credential_id=args.credential_id,
        login_username=args.login_username,
        max_concurrent=args.max_concurrent,
        max_posts=args.max_posts,
        skip_ai=args.skip_ai,
        json_output=args.json,
    )


def configure_runtime_secrets_from_settings() -> None:
    os.environ.setdefault(
        "SECRET_KEY_IG_CREDENTIALS",
        settings.SECRET_KEY_IG_CREDENTIALS,
    )
    if settings.OPENAI_API_KEY:
        os.environ.setdefault("OPENAI_API_KEY", settings.OPENAI_API_KEY)


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


def build_persistence(session: Session) -> BackendInstagramScrapePersistenceV2:
    return BackendInstagramScrapePersistenceV2(
        profiles_collection=session,
        posts_collection=session,
        reels_collection=session,
        metrics_collection=session,
        snapshots_collection=session,
    )


async def run_validation(options: ScriptOptions) -> SafePersistOutput:
    configure_runtime_secrets_from_settings()
    ping_postgres()
    config = build_config_from_options(options)
    payload = InstagramBatchScrapeRequest(
        usernames=list(options.usernames),
        timeout_ms=config.browser.timeout_ms,
        headless=config.browser.headless,
        locale=config.browser.locale,
        max_posts=options.max_posts,
        max_concurrent=config.crawler.max_concurrent,
        proxy=config.proxy.proxy_urls[0] if config.proxy.proxy_urls else None,
    )

    with Session(engine) as session:
        persistence = build_persistence(session)
        scrape_payload, early_response = await prepare_scrape_batch_payload(
            payload,
            persistence,
        )
        if early_response is not None:
            summary = build_batch_scrape_summary(
                payload,
                scrape_payload,
                None,
                early_response=early_response,
            )
            return build_safe_output(
                summary=summary.model_dump(),
                proxy_mode="decodo" if config.proxy.use_isp_proxy else "local",
                headless=config.browser.headless,
            )

        response = await InstagramBatchScrapeRunner(
            config=config,
            credentials_store=build_credentials_store(options),
            usernames=scrape_payload.usernames,
            max_posts=scrape_payload.max_posts,
        ).run_response()

        if not options.skip_ai:
            response = await enrich_with_ai_analysis(
                response,
                analysis_service=BackendInstagramProfileAnalysisServiceV2(),
            )

        response = await persist_scrape_results_to_db(
            response,
            persistence=persistence,
        )
        summary = build_batch_scrape_summary(payload, scrape_payload, response)
        return build_safe_output(
            summary=summary.model_dump(),
            proxy_mode="decodo" if config.proxy.use_isp_proxy else "local",
            headless=config.browser.headless,
        )


def build_safe_output(
    *,
    summary: dict,
    proxy_mode: str,
    headless: bool,
) -> SafePersistOutput:
    usernames = summary.get("usernames") or []
    return SafePersistOutput(
        success=not bool(summary.get("error"))
        and not any(item.get("status") == "failed" for item in usernames),
        error=summary.get("error"),
        proxy_mode=proxy_mode,
        headless=headless,
        counters=summary.get("counters") or {},
        summary=summary,
        persisted_usernames=[
            item["username"] for item in usernames if item.get("status") == "success"
        ],
        skipped_usernames=[
            item["username"] for item in usernames if item.get("status") == "skipped"
        ],
        not_found_usernames=[
            item["username"] for item in usernames if item.get("status") == "not_found"
        ],
        failed_usernames=[
            item["username"] for item in usernames if item.get("status") == "failed"
        ],
    )


def print_output(output: SafePersistOutput, *, json_output: bool) -> None:
    payload = asdict(output)
    if json_output:
        sys.stdout.write(f"{json.dumps(payload, sort_keys=True)}\n")
        return

    sys.stdout.write(f"success: {output.success}\n")
    sys.stdout.write(f"error: {output.error}\n")
    sys.stdout.write(f"proxy_mode: {output.proxy_mode}\n")
    sys.stdout.write(f"headless: {output.headless}\n")
    sys.stdout.write(f"counters: {output.counters}\n")
    sys.stdout.write(f"persisted_usernames: {output.persisted_usernames}\n")
    sys.stdout.write(f"skipped_usernames: {output.skipped_usernames}\n")
    sys.stdout.write(f"not_found_usernames: {output.not_found_usernames}\n")
    sys.stdout.write(f"failed_usernames: {output.failed_usernames}\n")


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
            output = SafePersistOutput(
                success=False,
                error=str(exc),
                proxy_mode="unknown",
                headless=True,
                counters={},
                summary={},
                persisted_usernames=[],
                skipped_usernames=[],
                not_found_usernames=[],
                failed_usernames=[],
            )
            print_output(output, json_output=json_output)
            return EXIT_CONFIG_ERROR
        raise


if __name__ == "__main__":
    raise SystemExit(main())
