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
    InstagramSessionBootstrapper,
    build_scraper_v2_config,
)
from kiizama_scrape_core.ig_scraper_v2.classes import (
    CredentialCandidate,
    SessionValidationResult,
)
from kiizama_scrape_core.ig_scraper_v2.ports import InstagramCredentialsStore
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine, ping_postgres
from app.features.ig_scraper_v2_runtime import BackendInstagramCredentialsStoreV2

EXIT_SUCCESS = 0
EXIT_VALIDATION_FAILED = 1
EXIT_CONFIG_ERROR = 2
EXIT_INTERRUPTED = 130


@dataclass(frozen=True, slots=True)
class ScriptOptions:
    headless: bool | None
    use_proxy: bool
    proxy_urls: tuple[str, ...] | None
    timeout_ms: int | None
    credential_id: str | None
    login_username: str | None
    json_output: bool


@dataclass(frozen=True, slots=True)
class SafeLoginValidationOutput:
    success: bool
    credential_id: str | None
    message: str
    error: str | None
    proxy_mode: str
    headless: bool
    storage_state_present: bool


class FilteredInstagramCredentialsStore(InstagramCredentialsStore):
    def __init__(
        self,
        store: InstagramCredentialsStore,
        *,
        credential_id: str | None = None,
        login_username: str | None = None,
    ) -> None:
        self._store = store
        self._credential_id = credential_id
        self._login_username = (
            login_username.strip().lower() if login_username else None
        )

    async def list_credentials(self, *, limit: int) -> list[CredentialCandidate]:
        credentials = await self._store.list_credentials(limit=limit)
        filtered: list[CredentialCandidate] = []
        for credential in credentials:
            if self._credential_id and credential.id != self._credential_id:
                continue
            if (
                self._login_username
                and (credential.login_username or "").strip().lower()
                != self._login_username
            ):
                continue
            filtered.append(credential)
        return filtered

    def decrypt_password(self, encrypted_password: str) -> str:
        return self._store.decrypt_password(encrypted_password)

    async def persist_session(
        self,
        credential_id: str,
        state: dict[str, Any],
    ) -> bool:
        return await self._store.persist_session(credential_id, state)


def parse_args(argv: list[str] | None = None) -> ScriptOptions:
    parser = argparse.ArgumentParser(
        description="Validate Instagram scraper v2 login/session against backend DB."
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
        help="Validate a specific private.ig_credentials id.",
    )
    parser.add_argument(
        "--login-username",
        default=None,
        help="Validate a specific Instagram login username.",
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


def build_filtered_credentials_store(
    *,
    credential_id: str | None,
    login_username: str | None,
) -> InstagramCredentialsStore:
    base_store = BackendInstagramCredentialsStoreV2(lambda: Session(engine))
    return FilteredInstagramCredentialsStore(
        base_store,
        credential_id=credential_id,
        login_username=login_username,
    )


def build_config_from_options(options: ScriptOptions):
    return build_scraper_v2_config(
        headless=options.headless,
        timeout_ms=options.timeout_ms,
        use_isp_proxy=options.use_proxy,
        proxy_urls=options.proxy_urls,
    )


def build_safe_output(
    result: SessionValidationResult,
    *,
    proxy_mode: str,
    headless: bool,
) -> SafeLoginValidationOutput:
    return SafeLoginValidationOutput(
        success=result.success,
        credential_id=result.credential_id,
        message=result.message,
        error=result.error,
        proxy_mode=proxy_mode,
        headless=headless,
        storage_state_present=bool(result.storage_state),
    )


def print_output(
    output: SafeLoginValidationOutput,
    *,
    json_output: bool,
) -> None:
    payload = asdict(output)
    if json_output:
        sys.stdout.write(f"{json.dumps(payload, sort_keys=True)}\n")
        return

    for key, value in payload.items():
        sys.stdout.write(f"{key}: {value}\n")


async def run_validation(options: ScriptOptions) -> SafeLoginValidationOutput:
    configure_secret_from_settings()
    ping_postgres()
    config = build_config_from_options(options)
    store = build_filtered_credentials_store(
        credential_id=options.credential_id,
        login_username=options.login_username,
    )
    result = await InstagramSessionBootstrapper(
        config=config,
        credentials_store=store,
    ).ensure_session()
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
        return EXIT_SUCCESS if output.success else EXIT_VALIDATION_FAILED
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED
    except Exception as exc:
        if _is_config_error(exc):
            output = SafeLoginValidationOutput(
                success=False,
                credential_id=None,
                message="Configuration or dependency error",
                error=str(exc),
                proxy_mode="unknown",
                headless=True,
                storage_state_present=False,
            )
            json_output = "--json" in (argv if argv is not None else sys.argv[1:])
            print_output(output, json_output=json_output)
            return EXIT_CONFIG_ERROR
        raise


if __name__ == "__main__":
    raise SystemExit(main())
