from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass

from kiizama_scrape_core.ig_scraper_v2 import (
    InstagramProfileOpenRunner,
    ProfileOpenRunResult,
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
EXIT_PROFILE_FAILED = 1
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
    json_output: bool


@dataclass(frozen=True, slots=True)
class SafeProfileOpenOutput:
    success: bool
    credential_id: str | None
    session_message: str
    error: str | None
    proxy_mode: str
    headless: bool
    results: list[dict[str, object]]


def parse_args(argv: list[str] | None = None) -> ScriptOptions:
    parser = argparse.ArgumentParser(
        description="Validate Instagram scraper v2 profile opening against backend DB."
    )
    parser.add_argument(
        "usernames",
        nargs="+",
        help="Instagram usernames to open and validate.",
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
        help="Validate profiles with a specific private.ig_credentials id.",
    )
    parser.add_argument(
        "--login-username",
        default=None,
        help="Validate profiles with a specific Instagram login username.",
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
    result: ProfileOpenRunResult,
    *,
    proxy_mode: str,
    headless: bool,
) -> SafeProfileOpenOutput:
    return SafeProfileOpenOutput(
        success=result.success,
        credential_id=result.credential_id,
        session_message=result.session_message,
        error=result.error,
        proxy_mode=proxy_mode,
        headless=headless,
        results=[
            {
                **asdict(profile_result),
                "status": profile_result.status.value,
            }
            for profile_result in result.results.values()
        ],
    )


def print_output(
    output: SafeProfileOpenOutput,
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
    for profile_result in output.results:
        sys.stdout.write(
            "profile: "
            f"{profile_result['requested_username']} "
            f"status={profile_result['status']} "
            f"success={profile_result['success']} "
            f"matched={profile_result['matched_username']} "
            f"error={profile_result['error']}\n"
        )


async def run_validation(options: ScriptOptions) -> SafeProfileOpenOutput:
    configure_secret_from_settings()
    ping_postgres()
    config = build_config_from_options(options)
    store = build_credentials_store(options)
    result = await InstagramProfileOpenRunner(
        config=config,
        credentials_store=store,
        usernames=list(options.usernames),
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
        return EXIT_SUCCESS if output.success else EXIT_PROFILE_FAILED
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED
    except SystemExit:
        raise
    except Exception as exc:
        if _is_config_error(exc):
            json_output = "--json" in (argv if argv is not None else sys.argv[1:])
            output = SafeProfileOpenOutput(
                success=False,
                credential_id=None,
                session_message="Configuration or dependency error",
                error=str(exc),
                proxy_mode="unknown",
                headless=True,
                results=[],
            )
            print_output(output, json_output=json_output)
            return EXIT_CONFIG_ERROR
        raise


if __name__ == "__main__":
    raise SystemExit(main())
