from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlencode

from kiizama_scrape_core.ig_scraper_v2 import (
    InstagramSessionBootstrapper,
    ScraperV2Config,
    build_effective_session_context,
    build_scraper_v2_config,
    sleep_for_next_delay,
)
from kiizama_scrape_core.ig_scraper_v2.browser import InstagramBrowserSession
from kiizama_scrape_core.ig_scraper_v2.profile_navigation import (
    build_profile_url,
    is_auth_lost_url,
    is_challenge_url,
    normalize_username,
)
from playwright.async_api import Page, Response
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine, ping_postgres
from app.features.ig_scraper_v2_runtime import BackendInstagramCredentialsStoreV2
from app.models import IgProfile
from scripts.validate_ig_v2_login import FilteredInstagramCredentialsStore

EXIT_SUCCESS = 0
EXIT_FOLLOWING_FAILED = 1
EXIT_CONFIG_ERROR = 2
EXIT_INTERRUPTED = 130

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "local_data" / "ig_following"

# Public Instagram web app id, echoed by the browser on private-API XHRs.
IG_WEB_APP_ID = "1217981644879628"

FRIENDSHIPS_FOLLOWING_RE = re.compile(r"/api/v1/friendships/(\d+)/following/")

# Headers the browser sends on the private following XHR that we replay verbatim
# on our controlled paginated requests. Cookies flow from the context jar, so the
# `cookie` header is intentionally excluded.
API_HEADER_WHITELIST: tuple[str, ...] = (
    "x-ig-app-id",
    "x-asbd-id",
    "x-csrftoken",
    "x-ig-www-claim",
    "x-requested-with",
    "x-web-session-id",
    "user-agent",
    "accept",
    "accept-language",
)

USERNAMES_PREVIEW_LIMIT = 15


@dataclass(frozen=True, slots=True)
class ScriptOptions:
    username: str
    ig_id: str | None
    count: int
    max_pages: int
    max_users: int | None
    start_max_id: str | None
    capture_timeout_seconds: float
    output_dir: Path
    headless: bool | None
    use_proxy: bool
    proxy_urls: tuple[str, ...] | None
    timeout_ms: int | None
    credential_id: str | None
    login_username: str | None
    json_output: bool


@dataclass(slots=True)
class FollowingPage:
    index: int
    url: str
    status: int
    max_id: str | None
    data: dict[str, Any]


@dataclass
class FollowingApiCapture:
    """Capture the first automatic friendships/following XHR the page fires.

    Not ``slots=True``: Playwright caches wrapped event handlers by setting an
    attribute on the handler's owning instance, which ``__slots__`` forbids.
    """

    logger: logging.Logger
    event: asyncio.Event = field(default_factory=asyncio.Event)
    ig_id: str | None = None
    status: int | None = None
    request_headers: dict[str, str] = field(default_factory=dict)
    response_headers: dict[str, str] = field(default_factory=dict)
    first_payload: dict[str, Any] | None = None

    async def handle_response(self, response: Response) -> None:
        if self.event.is_set():
            return
        match = FRIENDSHIPS_FOLLOWING_RE.search(response.url)
        if match is None:
            return
        try:
            request_headers = await response.request.all_headers()
            response_headers = await response.all_headers()
        except Exception as exc:  # pragma: no cover - IO variability
            self.logger.warning("Failed reading captured following headers: %s", exc)
            return

        payload: dict[str, Any] | None = None
        try:
            data = await response.json()
            if isinstance(data, dict):
                payload = data
        except Exception:
            payload = None

        self.ig_id = match.group(1)
        self.status = response.status
        self.request_headers = request_headers
        self.response_headers = response_headers
        self.first_payload = payload
        self.event.set()

    def attach(self, page: Page) -> None:
        page.on("response", self.handle_response)

    def detach(self, page: Page) -> None:
        try:
            page.remove_listener("response", self.handle_response)
        except Exception as exc:  # pragma: no cover - listener cleanup variability
            self.logger.warning("Failed to remove following listener: %s", exc)


@dataclass(frozen=True, slots=True)
class SafeFollowingOutput:
    success: bool
    username: str
    ig_id: str | None
    ig_id_source: str | None
    ig_id_db: str | None
    ig_id_captured: str | None
    ig_id_matches_db: bool | None
    credential_id: str | None
    session_message: str
    error: str | None
    proxy_mode: str
    headless: bool
    count: int
    pages_fetched: int
    total_users: int
    has_more_last_page: bool
    next_max_id_last: str | None
    output_dir: str | None
    usernames_preview: list[str]


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a valid integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def parse_args(argv: list[str] | None = None) -> ScriptOptions:
    parser = argparse.ArgumentParser(
        description=(
            "Log in to Instagram, open a profile, and page through its "
            "following list via the private friendships API into local_data/."
        )
    )
    parser.add_argument(
        "username",
        help="Instagram username whose following list to fetch (e.g. kimiish).",
    )
    parser.add_argument(
        "--ig-id",
        default=None,
        help="Skip id resolution and use this friendships id (the stored ig_id).",
    )
    parser.add_argument(
        "--count",
        type=positive_int,
        default=12,
        help="Page size per request (Instagram default is 12; try 50 to experiment).",
    )
    parser.add_argument(
        "--max-pages",
        type=positive_int,
        default=5,
        help="Maximum number of paginated requests to issue.",
    )
    parser.add_argument(
        "--max-users",
        type=positive_int,
        default=None,
        help="Stop once this many unique users are collected.",
    )
    parser.add_argument(
        "--start-max-id",
        default=None,
        help="Start pagination from this max_id cursor instead of page one.",
    )
    parser.add_argument(
        "--capture-timeout",
        type=float,
        default=15.0,
        dest="capture_timeout",
        help="Seconds to wait for the automatic following XHR before falling back.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to write results into (defaults to local_data/ig_following).",
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
        type=positive_int,
        default=None,
        help="Playwright navigation timeout in milliseconds.",
    )
    parser.add_argument(
        "--credential-id",
        default=None,
        help="Use a specific private.ig_credentials id.",
    )
    parser.add_argument(
        "--login-username",
        default=None,
        help="Use a specific Instagram login username.",
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
        username=args.username,
        ig_id=args.ig_id,
        count=args.count,
        max_pages=args.max_pages,
        max_users=args.max_users,
        start_max_id=args.start_max_id,
        capture_timeout_seconds=args.capture_timeout,
        output_dir=args.output_dir or DEFAULT_OUTPUT_DIR,
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


def build_config_from_options(options: ScriptOptions) -> ScraperV2Config:
    return build_scraper_v2_config(
        headless=options.headless,
        timeout_ms=options.timeout_ms,
        use_isp_proxy=options.use_proxy,
        proxy_urls=options.proxy_urls,
    )


def build_credentials_store(
    options: ScriptOptions,
) -> FilteredInstagramCredentialsStore:
    base_store = BackendInstagramCredentialsStoreV2(lambda: Session(engine))
    return FilteredInstagramCredentialsStore(
        base_store,
        credential_id=options.credential_id,
        login_username=options.login_username,
    )


def lookup_ig_id_from_db(username: str) -> str | None:
    normalized = normalize_username(username)
    if not normalized:
        return None
    username_column = cast(Any, IgProfile.username)
    with Session(engine) as session:
        return session.exec(
            select(IgProfile.ig_id).where(username_column == normalized)
        ).first()


def resolve_ig_id(
    options: ScriptOptions,
    capture: FollowingApiCapture,
    ig_id_db: str | None,
) -> tuple[str | None, str | None]:
    if options.ig_id:
        return options.ig_id, "cli"
    if capture.ig_id:
        return capture.ig_id, "captured"
    if ig_id_db:
        return ig_id_db, "db"
    return None, None


async def read_csrftoken(context: Any) -> str | None:
    if context is None:
        return None
    try:
        cookies = await context.cookies("https://www.instagram.com")
    except Exception:
        return None
    for cookie in cookies:
        if cookie.get("name") == "csrftoken":
            value = cookie.get("value")
            return value if isinstance(value, str) else None
    return None


def build_api_headers(
    *,
    capture: FollowingApiCapture,
    user_agent: str,
    csrftoken: str | None,
    referer: str,
) -> dict[str, str]:
    request_headers = {
        key.lower(): value for key, value in capture.request_headers.items()
    }
    response_headers = {
        key.lower(): value for key, value in capture.response_headers.items()
    }

    headers: dict[str, str] = {}
    for key in API_HEADER_WHITELIST:
        value = request_headers.get(key)
        if value:
            headers[key] = value

    # Instagram returns the fresh www-claim on the response; prefer it.
    claim = response_headers.get("x-ig-set-www-claim") or request_headers.get(
        "x-ig-www-claim"
    )
    if claim:
        headers["x-ig-www-claim"] = claim

    headers.setdefault("x-ig-app-id", IG_WEB_APP_ID)
    headers.setdefault("x-requested-with", "XMLHttpRequest")
    headers.setdefault("accept", "*/*")
    headers.setdefault("user-agent", user_agent)
    if csrftoken:
        headers.setdefault("x-csrftoken", csrftoken)
    headers["referer"] = referer
    return headers


def build_following_api_url(ig_id: str, *, count: int, max_id: str | None) -> str:
    params: dict[str, Any] = {"count": count}
    if max_id:
        params["max_id"] = max_id
    return (
        f"https://www.instagram.com/api/v1/friendships/{ig_id}/following/"
        f"?{urlencode(params)}"
    )


async def fetch_following_pages(
    page: Page,
    *,
    ig_id: str,
    headers: dict[str, str],
    options: ScriptOptions,
    config: Any,
    logger: logging.Logger,
) -> list[FollowingPage]:
    pages: list[FollowingPage] = []
    rng = random.Random()
    max_id = options.start_max_id
    collected_users = 0

    for page_index in range(1, options.max_pages + 1):
        url = build_following_api_url(ig_id, count=options.count, max_id=max_id)
        response = await page.request.get(url, headers=headers)
        status = response.status
        try:
            data = await response.json()
        except Exception:
            body = await response.text()
            logger.error(
                "Non-JSON following response (page=%s, status=%s): %s",
                page_index,
                status,
                body[:200],
            )
            pages.append(
                FollowingPage(
                    index=page_index,
                    url=url,
                    status=status,
                    max_id=max_id,
                    data={"error": "non_json_response", "body_preview": body[:200]},
                )
            )
            break

        if not isinstance(data, dict):
            data = {"error": "unexpected_payload"}

        pages.append(
            FollowingPage(
                index=page_index,
                url=url,
                status=status,
                max_id=max_id,
                data=data,
            )
        )

        raw_users = data.get("users")
        page_users = raw_users if isinstance(raw_users, list) else []
        collected_users += len(page_users)
        logger.info(
            "Fetched following page %s (status=%s, users=%s, max_id=%s)",
            page_index,
            status,
            len(page_users),
            max_id or "<start>",
        )

        if status != 200:
            break
        if options.max_users is not None and collected_users >= options.max_users:
            break

        has_more = bool(data.get("has_more"))
        next_max_id = data.get("next_max_id")
        if not has_more or not next_max_id:
            break
        max_id = str(next_max_id)

        if page_index < options.max_pages:
            await sleep_for_next_delay(config.pacing, sleeper=asyncio.sleep, rng=rng)

    return pages


def extract_users(pages: list[FollowingPage]) -> list[dict[str, Any]]:
    users: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page in pages:
        raw_users = page.data.get("users")
        if not isinstance(raw_users, list):
            continue
        for user in raw_users:
            if not isinstance(user, dict):
                continue
            key = str(
                user.get("pk") or user.get("pk_id") or user.get("id") or ""
            ) or str(user.get("username") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            users.append(user)
    return users


def extract_usernames(users: list[dict[str, Any]]) -> list[str]:
    usernames: list[str] = []
    for user in users:
        username = user.get("username")
        if isinstance(username, str) and username:
            usernames.append(username)
    return usernames


def timestamp_for_dir(now: datetime | None = None) -> str:
    current = now or datetime.now(UTC)
    return current.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def resolve_output_dir(options: ScriptOptions, username: str) -> Path:
    return options.output_dir / username / timestamp_for_dir()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def save_outputs(
    output_dir: Path,
    *,
    username: str,
    ig_id: str,
    ig_id_source: str | None,
    count: int,
    pages: list[FollowingPage],
    users: list[dict[str, Any]],
    usernames: list[str],
    capture: FollowingApiCapture,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for page in pages:
        write_json(output_dir / f"page_{page.index:02d}.json", page.data)

    if capture.first_payload is not None:
        write_json(output_dir / "captured_auto_page.json", capture.first_payload)

    write_json(output_dir / "following_users.json", users)
    (output_dir / "usernames.txt").write_text(
        "\n".join(usernames) + ("\n" if usernames else ""),
        encoding="utf-8",
    )

    last_page = pages[-1] if pages else None
    write_json(
        output_dir / "summary.json",
        {
            "username": username,
            "ig_id": ig_id,
            "ig_id_source": ig_id_source,
            "count": count,
            "pages_fetched": len(pages),
            "total_users": len(users),
            "total_usernames": len(usernames),
            "has_more_last_page": bool(last_page and last_page.data.get("has_more")),
            "next_max_id_last": (
                str(last_page.data.get("next_max_id"))
                if last_page and last_page.data.get("next_max_id")
                else None
            ),
            "pages": [
                {
                    "index": page.index,
                    "status": page.status,
                    "max_id": page.max_id,
                    "url": page.url,
                    "users": len(page.data.get("users") or [])
                    if isinstance(page.data.get("users"), list)
                    else 0,
                }
                for page in pages
            ],
        },
    )


def _session_failure(
    *,
    username: str,
    session_result: Any,
    config: Any,
) -> SafeFollowingOutput:
    return SafeFollowingOutput(
        success=False,
        username=username,
        ig_id=None,
        ig_id_source=None,
        ig_id_db=None,
        ig_id_captured=None,
        ig_id_matches_db=None,
        credential_id=session_result.credential_id,
        session_message=session_result.message,
        error=session_result.error or session_result.message,
        proxy_mode="decodo" if config.proxy.use_isp_proxy else "local",
        headless=config.browser.headless,
        count=0,
        pages_fetched=0,
        total_users=0,
        has_more_last_page=False,
        next_max_id_last=None,
        output_dir=None,
        usernames_preview=[],
    )


async def run_following(options: ScriptOptions) -> SafeFollowingOutput:
    logger = logging.getLogger("scripts.validate_ig_v2_following")
    configure_secret_from_settings()
    ping_postgres()

    config = build_config_from_options(options)
    proxy_mode = "decodo" if config.proxy.use_isp_proxy else "local"
    store = build_credentials_store(options)

    session_result = await InstagramSessionBootstrapper(
        config=config,
        credentials_store=store,
    ).ensure_session()
    if not session_result.success:
        return _session_failure(
            username=normalize_username(options.username),
            session_result=session_result,
            config=config,
        )

    effective = build_effective_session_context(config, session_result.storage_state)
    username = normalize_username(options.username)
    following_url = f"{build_profile_url(username)}following/"

    ig_id_db = None if options.ig_id else lookup_ig_id_from_db(username)

    browser_session = InstagramBrowserSession(
        config=effective.config,
        storage_state=effective.storage_state,
        extra_http_headers=effective.extra_http_headers,
        credential_id=session_result.credential_id,
    )

    capture = FollowingApiCapture(logger=logger)
    navigation_error: str | None = None
    pages: list[FollowingPage] = []

    async with browser_session as browser:
        page = browser.page
        context = browser.context
        if page is None or context is None:
            navigation_error = "Playwright page could not be initialized"
        else:
            capture.attach(page)
            try:
                await browser.retryable_goto(
                    page,
                    following_url,
                    wait_until="domcontentloaded",
                    timeout=effective.config.browser.timeout_ms,
                )
            except Exception as exc:
                navigation_error = f"Error loading following page after retries: {exc}"

            final_url = getattr(page, "url", "")
            if navigation_error is None and is_auth_lost_url(final_url):
                navigation_error = "Instagram session redirected to login"
            elif navigation_error is None and is_challenge_url(final_url):
                navigation_error = "Instagram challenge or 2FA required"

            if navigation_error is None:
                try:
                    await asyncio.wait_for(
                        capture.event.wait(),
                        timeout=options.capture_timeout_seconds,
                    )
                except TimeoutError:
                    logger.info(
                        "No automatic following XHR captured within %.1fs; "
                        "falling back to constructed headers.",
                        options.capture_timeout_seconds,
                    )

                ig_id, ig_id_source = resolve_ig_id(options, capture, ig_id_db)
                if ig_id is None:
                    navigation_error = (
                        "Could not resolve friendships id (no --ig-id, no captured "
                        "XHR, and no DB match for this username)."
                    )
                else:
                    csrftoken = await read_csrftoken(context)
                    headers = build_api_headers(
                        capture=capture,
                        user_agent=effective.config.browser.user_agent,
                        csrftoken=csrftoken,
                        referer=following_url,
                    )
                    pages = await fetch_following_pages(
                        page,
                        ig_id=ig_id,
                        headers=headers,
                        options=options,
                        config=effective.config,
                        logger=logger,
                    )

            capture.detach(page)

    if navigation_error is not None:
        return SafeFollowingOutput(
            success=False,
            username=username,
            ig_id=None,
            ig_id_source=None,
            ig_id_db=ig_id_db,
            ig_id_captured=capture.ig_id,
            ig_id_matches_db=_ig_id_matches_db(capture.ig_id, ig_id_db),
            credential_id=session_result.credential_id,
            session_message=session_result.message,
            error=navigation_error,
            proxy_mode=proxy_mode,
            headless=effective.config.browser.headless,
            count=options.count,
            pages_fetched=0,
            total_users=0,
            has_more_last_page=False,
            next_max_id_last=None,
            output_dir=None,
            usernames_preview=[],
        )

    ig_id, ig_id_source = resolve_ig_id(options, capture, ig_id_db)
    assert ig_id is not None  # navigation_error would be set otherwise
    users = extract_users(pages)
    usernames = extract_usernames(users)
    output_dir = resolve_output_dir(options, username)
    save_outputs(
        output_dir,
        username=username,
        ig_id=ig_id,
        ig_id_source=ig_id_source,
        count=options.count,
        pages=pages,
        users=users,
        usernames=usernames,
        capture=capture,
    )

    last_page = pages[-1] if pages else None
    first_status_ok = bool(pages) and pages[0].status == 200
    return SafeFollowingOutput(
        success=first_status_ok,
        username=username,
        ig_id=ig_id,
        ig_id_source=ig_id_source,
        ig_id_db=ig_id_db,
        ig_id_captured=capture.ig_id,
        ig_id_matches_db=_ig_id_matches_db(capture.ig_id, ig_id_db),
        credential_id=session_result.credential_id,
        session_message=session_result.message,
        error=None if first_status_ok else "Following API did not return HTTP 200",
        proxy_mode=proxy_mode,
        headless=effective.config.browser.headless,
        count=options.count,
        pages_fetched=len(pages),
        total_users=len(users),
        has_more_last_page=bool(last_page and last_page.data.get("has_more")),
        next_max_id_last=(
            str(last_page.data.get("next_max_id"))
            if last_page and last_page.data.get("next_max_id")
            else None
        ),
        output_dir=str(output_dir),
        usernames_preview=usernames[:USERNAMES_PREVIEW_LIMIT],
    )


def _ig_id_matches_db(captured: str | None, ig_id_db: str | None) -> bool | None:
    if captured is None or ig_id_db is None:
        return None
    return captured == ig_id_db


def print_output(output: SafeFollowingOutput, *, json_output: bool) -> None:
    payload = asdict(output)
    if json_output:
        sys.stdout.write(f"{json.dumps(payload, sort_keys=True)}\n")
        return
    for key, value in payload.items():
        sys.stdout.write(f"{key}: {value}\n")


def _is_config_error(exc: Exception) -> bool:
    return isinstance(
        exc,
        (
            FileNotFoundError,
            ValueError,
            ValidationError,
            SQLAlchemyError,
            RuntimeError,
        ),
    )


def _json_requested(argv: list[str] | None) -> bool:
    args = argv if argv is not None else sys.argv[1:]
    return "--json" in args


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    try:
        options = parse_args(argv)
        output = asyncio.run(run_following(options))
        print_output(output, json_output=options.json_output)
        return EXIT_SUCCESS if output.success else EXIT_FOLLOWING_FAILED
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED
    except SystemExit:
        raise
    except Exception as exc:
        if _is_config_error(exc):
            output = SafeFollowingOutput(
                success=False,
                username="",
                ig_id=None,
                ig_id_source=None,
                ig_id_db=None,
                ig_id_captured=None,
                ig_id_matches_db=None,
                credential_id=None,
                session_message="Configuration or dependency error",
                error=str(exc),
                proxy_mode="unknown",
                headless=True,
                count=0,
                pages_fetched=0,
                total_users=0,
                has_more_last_page=False,
                next_max_id_last=None,
                output_dir=None,
                usernames_preview=[],
            )
            print_output(output, json_output=_json_requested(argv))
            return EXIT_CONFIG_ERROR
        raise


if __name__ == "__main__":
    raise SystemExit(main())
