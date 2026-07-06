from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, cast

from kiizama_scrape_core.ig_scraper_v2 import (
    InstagramBatchScrapeRunner,
    InstagramProfileNavigator,
    InstagramScrapeCollector,
    InstagramSessionBootstrapper,
    ProfileOpenStatus,
    ScraperV2Config,
    build_effective_session_context,
    build_scraper_v2_config,
    enrich_with_ai_analysis,
    persist_scrape_results_to_db,
    sleep_for_next_delay,
)
from kiizama_scrape_core.ig_scraper_v2.browser import InstagramBrowserSession
from kiizama_scrape_core.ig_scraper_v2.parsers import parse_user_info
from kiizama_scrape_core.ig_scraper_v2.profile_navigation import (
    normalize_username,
    profile_not_found,
)
from kiizama_scrape_core.ig_scraper_v2.profile_scraper import (
    extract_user_info_from_scripts,
)
from kiizama_scrape_core.ig_scraper_v2.schemas import InstagramBatchScrapeResponse
from kiizama_scrape_core.ig_scraper_v2.stealth import add_stealth
from kiizama_scrape_core.ig_scraper_v2.utils import should_refresh_profile
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine, ping_postgres
from app.features.ig_scraper_v2_runtime import (
    BackendInstagramCredentialsStoreV2,
    BackendInstagramProfileAnalysisServiceV2,
    BackendInstagramScrapePersistenceV2,
)
from app.models import IgProfile
from scripts.validate_ig_v2_login import FilteredInstagramCredentialsStore

EXIT_SUCCESS = 0
EXIT_RUN_FAILED = 1
EXIT_CONFIG_ERROR = 2
EXIT_INTERRUPTED = 130

NOT_FOUND_ERROR = "Instagram username does not exist"

# Statuses that are final for a username and are never re-processed on later runs.
TERMINAL_STATUSES = frozenset(
    {"done", "skipped_low_followers", "skipped_existing", "not_found"}
)
# Transient failures only re-processed when --retry-failed is passed.
RETRYABLE_FAILURE_STATUSES = frozenset({"failed", "precheck_failed"})


@dataclass(frozen=True, slots=True)
class ScriptOptions:
    input_path: Path
    status_path: Path | None
    min_followers: int
    max_profiles: int
    max_prechecks: int | None
    precheck_timeout: float
    batch_size: int
    sleep_between_batches: float
    force_refresh: bool
    retry_failed: bool
    skip_ai: bool
    max_posts: int
    headless: bool | None
    use_proxy: bool
    proxy_urls: tuple[str, ...] | None
    timeout_ms: int | None
    max_concurrent: int | None
    credential_id: str | None
    login_username: str | None
    json_output: bool


@dataclass(frozen=True, slots=True)
class PrecheckResult:
    status: str  # "ok" | "not_found" | "failed"
    followers: int | None = None
    ig_id: str | None = None
    is_private: bool | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class SafeOutput:
    success: bool
    input_path: str
    status_path: str | None
    total_input: int
    processable: int
    skipped_existing: int
    prechecked: int
    passed_precheck: int
    skipped_low_followers: int
    not_found: int
    precheck_failed: int
    scraped_ok: int
    persist_failed: int
    min_followers: int
    max_profiles: int
    error: str | None


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a valid integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def non_negative_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a valid number") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def parse_args(argv: list[str] | None = None) -> ScriptOptions:
    parser = argparse.ArgumentParser(
        description=(
            "Read usernames from an ig_following export, precheck each profile's "
            "follower count, then scrape and persist only those above a threshold, "
            "in controlled batches."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        dest="input_path",
        help="Path to a following export (following_users.json or usernames.txt).",
    )
    parser.add_argument(
        "--status-file",
        type=Path,
        default=None,
        dest="status_path",
        help="Progress/resume file (defaults to <input>.persist_status.json).",
    )
    parser.add_argument(
        "--min-followers",
        type=positive_int,
        default=1500,
        help="Minimum follower count required before scraping/persisting a profile.",
    )
    parser.add_argument(
        "--max-profiles",
        type=positive_int,
        default=150,
        help="Maximum profiles to scrape and persist per run (volume control).",
    )
    parser.add_argument(
        "--max-prechecks",
        type=positive_int,
        default=None,
        help="Safety cap on follower micro-scrapes issued per run.",
    )
    parser.add_argument(
        "--precheck-timeout",
        type=non_negative_float,
        default=20.0,
        help="Seconds to wait for profile data during the follower micro-scrape.",
    )
    parser.add_argument(
        "--batch-size",
        type=positive_int,
        default=25,
        help="Profiles scraped and persisted per batch.",
    )
    parser.add_argument(
        "--sleep-between-batches",
        type=non_negative_float,
        default=45.0,
        help="Seconds to pause between scrape/persist batches (time control).",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Process profiles even if already present and fresh in the database.",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Re-process usernames previously marked failed or precheck_failed.",
    )
    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Skip AI enrichment while persisting.",
    )
    parser.add_argument(
        "--max-posts",
        type=positive_int,
        default=12,
        help="Maximum posts and reels to collect per profile.",
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
        "--max-concurrent",
        type=positive_int,
        default=None,
        help="Maximum concurrent profile pages during scraping.",
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

    return ScriptOptions(
        input_path=args.input_path,
        status_path=args.status_path,
        min_followers=args.min_followers,
        max_profiles=args.max_profiles,
        max_prechecks=args.max_prechecks,
        precheck_timeout=args.precheck_timeout,
        batch_size=args.batch_size,
        sleep_between_batches=args.sleep_between_batches,
        force_refresh=args.force_refresh,
        retry_failed=args.retry_failed,
        skip_ai=args.skip_ai,
        max_posts=args.max_posts,
        headless=headless,
        use_proxy=args.use_proxy,
        proxy_urls=tuple(args.proxy_url) if args.proxy_url else None,
        timeout_ms=args.timeout_ms,
        max_concurrent=args.max_concurrent,
        credential_id=args.credential_id,
        login_username=args.login_username,
        json_output=args.json,
    )


def configure_runtime_secrets_from_settings() -> None:
    os.environ.setdefault(
        "SECRET_KEY_IG_CREDENTIALS",
        settings.SECRET_KEY_IG_CREDENTIALS,
    )
    if settings.OPENAI_API_KEY:
        os.environ.setdefault("OPENAI_API_KEY", settings.OPENAI_API_KEY)


def build_config_from_options(options: ScriptOptions) -> ScraperV2Config:
    return build_scraper_v2_config(
        headless=options.headless,
        timeout_ms=options.timeout_ms,
        max_concurrent=options.max_concurrent,
        max_posts=options.max_posts,
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


def build_persistence(session: Session) -> BackendInstagramScrapePersistenceV2:
    return BackendInstagramScrapePersistenceV2(
        profiles_collection=session,
        posts_collection=session,
        reels_collection=session,
        metrics_collection=session,
        snapshots_collection=session,
    )


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def resolve_status_path(options: ScriptOptions) -> Path:
    if options.status_path is not None:
        return options.status_path
    input_path = options.input_path
    return input_path.with_name(f"{input_path.stem}.persist_status.json")


def load_input_usernames(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    raw_usernames: list[str] = []
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, str):
                    raw_usernames.append(entry)
                elif isinstance(entry, dict):
                    username = entry.get("username")
                    if isinstance(username, str):
                        raw_usernames.append(username)
        elif isinstance(data, dict):
            users = data.get("users")
            if isinstance(users, list):
                for entry in users:
                    if isinstance(entry, dict) and isinstance(
                        entry.get("username"), str
                    ):
                        raw_usernames.append(entry["username"])
    else:
        raw_usernames = path.read_text(encoding="utf-8").splitlines()

    deduped: list[str] = []
    seen: set[str] = set()
    for raw in raw_usernames:
        username = normalize_username(raw)
        if not username or username in seen:
            continue
        seen.add(username)
        deduped.append(username)
    return deduped


def load_status(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, dict):
        return {}
    return {
        str(username): value
        for username, value in records.items()
        if isinstance(value, dict)
    }


def save_status(path: Path, records: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"updated_at": utcnow_iso(), "records": records}
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as temp_file:
        json.dump(payload, temp_file, ensure_ascii=False, indent=2, sort_keys=True)
        temp_path = Path(temp_file.name)
    temp_path.replace(path)


def is_processable(record: dict[str, Any] | None, *, retry_failed: bool) -> bool:
    if not record:
        return True
    status = record.get("status")
    if status in TERMINAL_STATUSES:
        return False
    if status in RETRYABLE_FAILURE_STATUSES and not retry_failed:
        return False
    return True


def fetch_existing_profiles(usernames: list[str]) -> dict[str, dict[str, Any]]:
    normalized = sorted({normalize_username(u) for u in usernames if u})
    if not normalized:
        return {}
    username_column = cast(Any, IgProfile.username)
    with Session(engine) as session:
        rows = session.exec(
            select(IgProfile.username, IgProfile.profile_pic_url).where(
                username_column.in_(normalized)
            )
        ).all()
    return {normalize_username(row[0]): {"profile_pic_url": row[1]} for row in rows}


async def _wait_for_user_info(
    collector: InstagramScrapeCollector, timeout_s: float
) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while loop.time() < deadline:
        if collector.user_info:
            return True
        await asyncio.sleep(0.4)
    return bool(collector.user_info)


async def micro_scrape_follower_info(
    context: Any,
    username: str,
    *,
    config: ScraperV2Config,
    retryable_goto: Any,
    logger: logging.Logger,
    timeout_s: float,
) -> PrecheckResult:
    """Reuse the real scrape's profile navigation + user_info extraction, but
    stop as soon as the profile header (with follower_count) is captured.

    This is a trimmed copy of ``InstagramProfileScraper.scrape``: same
    navigator, same ``InstagramScrapeCollector`` and same script fallback, but
    it never waits for or collects posts/reels.
    """
    page = await context.new_page()
    try:
        await add_stealth(page, locale=config.browser.locale, logger=logger)
        collector = InstagramScrapeCollector(
            max_posts=1,
            target_username=username,
            logger=logger,
            collect_posts=True,
            collect_reels=False,
            collect_recommendations=False,
        )
        collector.attach(page)
        try:
            navigator = InstagramProfileNavigator(
                config=config,
                retryable_goto=retryable_goto,
                logger=logger,
            )
            open_result = await navigator.open_profile(page, username)
            if not open_result.success:
                if open_result.status == ProfileOpenStatus.NOT_FOUND:
                    return PrecheckResult(status="not_found")
                return PrecheckResult(status="failed", error=open_result.error)

            if not await _wait_for_user_info(collector, timeout_s):
                try:
                    await page.reload(
                        wait_until="domcontentloaded",
                        timeout=config.browser.timeout_ms,
                    )
                    await _wait_for_user_info(collector, 5)
                except Exception as exc:
                    logger.debug(
                        "Reload during micro-scrape failed for %s: %s", username, exc
                    )
        finally:
            collector.detach(page)

        user_info = collector.user_info
        if not user_info:
            user_info = await extract_user_info_from_scripts(
                page, target_username=username
            )

        profile = parse_user_info(user_info or {})
        if not profile.username:
            if await profile_not_found(page):
                return PrecheckResult(status="not_found")
            return PrecheckResult(
                status="failed", error="Unable to collect profile data"
            )

        return PrecheckResult(
            status="ok",
            followers=profile.follower_count,
            ig_id=profile.id,
            is_private=profile.is_private,
        )
    finally:
        await page.close()


async def run_precheck_phase(
    options: ScriptOptions,
    *,
    candidates: list[str],
    status: dict[str, dict[str, Any]],
    status_path: Path,
    logger: logging.Logger,
) -> list[str]:
    config = build_config_from_options(options)
    store = build_credentials_store(options)
    session_result = await InstagramSessionBootstrapper(
        config=config,
        credentials_store=store,
    ).ensure_session()
    if not session_result.success:
        raise RuntimeError(
            session_result.error or session_result.message or "Session bootstrap failed"
        )

    effective = build_effective_session_context(config, session_result.storage_state)
    rng = random.Random()
    to_scrape: list[str] = []
    prechecks_done = 0

    browser_session = InstagramBrowserSession(
        config=effective.config,
        storage_state=effective.storage_state,
        extra_http_headers=effective.extra_http_headers,
        credential_id=session_result.credential_id,
    )

    async with browser_session as browser:
        context = browser.context
        if context is None:
            raise RuntimeError("Playwright browser context could not be initialized")

        for username in candidates:
            if len(to_scrape) >= options.max_profiles:
                break
            if options.max_prechecks is not None and prechecks_done >= (
                options.max_prechecks
            ):
                break

            result = await micro_scrape_follower_info(
                context,
                username,
                config=effective.config,
                retryable_goto=browser.retryable_goto,
                logger=logger,
                timeout_s=options.precheck_timeout,
            )
            prechecks_done += 1
            record = status.setdefault(username, {})
            record["precheck_at"] = utcnow_iso()
            record["followers"] = result.followers
            record["ig_id"] = result.ig_id
            record["is_private"] = result.is_private

            if result.status == "not_found":
                record["status"] = "not_found"
                record["error"] = "not_found"
            elif result.status == "failed":
                record["status"] = "precheck_failed"
                record["error"] = result.error
            elif result.followers is None:
                # Header never yielded a follower count: retry on a later run
                # rather than silently dropping the profile.
                record["status"] = "precheck_failed"
                record["error"] = "follower_count_unavailable"
            elif result.followers >= options.min_followers:
                record["status"] = "passed_precheck"
                record["error"] = None
                to_scrape.append(username)
            else:
                record["status"] = "skipped_low_followers"
                record["error"] = None

            save_status(status_path, status)
            logger.info(
                "Precheck %s -> status=%s followers=%s",
                username,
                record["status"],
                result.followers,
            )

            await sleep_for_next_delay(
                effective.config.pacing, sleeper=asyncio.sleep, rng=rng
            )

    return to_scrape


async def scrape_and_persist_batch(
    options: ScriptOptions, usernames: list[str]
) -> InstagramBatchScrapeResponse:
    config = build_config_from_options(options)
    response = await InstagramBatchScrapeRunner(
        config=config,
        credentials_store=build_credentials_store(options),
        usernames=usernames,
        max_posts=options.max_posts,
    ).run_response()

    if not options.skip_ai:
        response = await enrich_with_ai_analysis(
            response,
            analysis_service=BackendInstagramProfileAnalysisServiceV2(),
        )

    with Session(engine) as session:
        response = await persist_scrape_results_to_db(
            response,
            persistence=build_persistence(session),
        )
    return response


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[start : start + size] for start in range(0, len(items), size)]


async def run_persist_phase(
    options: ScriptOptions,
    *,
    to_scrape: list[str],
    status: dict[str, dict[str, Any]],
    status_path: Path,
    logger: logging.Logger,
) -> None:
    rng = random.Random()
    batches = chunked(to_scrape, options.batch_size)
    for batch_index, batch in enumerate(batches, start=1):
        logger.info(
            "Scrape/persist batch %s/%s (size=%s)",
            batch_index,
            len(batches),
            len(batch),
        )
        response = await scrape_and_persist_batch(options, batch)
        processed_at = utcnow_iso()
        for username in batch:
            record = status.setdefault(username, {})
            record["processed_at"] = processed_at
            result = response.results.get(username)
            if result is None:
                record["status"] = "failed"
                record["error"] = response.error or "Missing scrape result"
            elif result.success:
                record["status"] = "done"
                record["error"] = None
                record["followers"] = result.user.follower_count
            elif result.error == NOT_FOUND_ERROR:
                record["status"] = "not_found"
                record["error"] = result.error
            else:
                record["status"] = "failed"
                record["error"] = result.error or response.error or "Scrape failed"
        save_status(status_path, status)

        if batch_index < len(batches) and options.sleep_between_batches > 0:
            await asyncio.sleep(options.sleep_between_batches)
        elif batch_index < len(batches):
            await sleep_for_next_delay(
                build_config_from_options(options).pacing,
                sleeper=asyncio.sleep,
                rng=rng,
            )


def build_output(
    options: ScriptOptions,
    *,
    status_path: Path,
    total_input: int,
    processable: int,
    skipped_existing: int,
    status: dict[str, dict[str, Any]],
    error: str | None = None,
) -> SafeOutput:
    def count(target: str) -> int:
        return sum(1 for record in status.values() if record.get("status") == target)

    done = count("done")
    persist_failed = count("failed")
    prechecked = sum(1 for record in status.values() if record.get("precheck_at"))
    return SafeOutput(
        success=error is None and persist_failed == 0,
        input_path=str(options.input_path),
        status_path=str(status_path),
        total_input=total_input,
        processable=processable,
        skipped_existing=skipped_existing,
        prechecked=prechecked,
        passed_precheck=done + count("passed_precheck"),
        skipped_low_followers=count("skipped_low_followers"),
        not_found=count("not_found"),
        precheck_failed=count("precheck_failed"),
        scraped_ok=done,
        persist_failed=persist_failed,
        min_followers=options.min_followers,
        max_profiles=options.max_profiles,
        error=error,
    )


async def run(options: ScriptOptions) -> SafeOutput:
    logger = logging.getLogger("scripts.ig_following_persist_pipeline")
    configure_runtime_secrets_from_settings()
    ping_postgres()

    status_path = resolve_status_path(options)
    input_usernames = load_input_usernames(options.input_path)
    status = load_status(status_path)

    candidates = [
        username
        for username in input_usernames
        if is_processable(status.get(username), retry_failed=options.retry_failed)
    ]

    skipped_existing = 0
    if not options.force_refresh and candidates:
        existing = fetch_existing_profiles(candidates)
        remaining: list[str] = []
        for username in candidates:
            profile = existing.get(username)
            if profile is not None and not should_refresh_profile(profile):
                record = status.setdefault(username, {})
                record["status"] = "skipped_existing"
                record["error"] = None
                skipped_existing += 1
            else:
                remaining.append(username)
        candidates = remaining
        save_status(status_path, status)

    processable = len(candidates)
    if not candidates:
        logger.info("No processable usernames; nothing to do.")
        return build_output(
            options,
            status_path=status_path,
            total_input=len(input_usernames),
            processable=processable,
            skipped_existing=skipped_existing,
            status=status,
        )

    to_scrape = await run_precheck_phase(
        options,
        candidates=candidates,
        status=status,
        status_path=status_path,
        logger=logger,
    )

    if to_scrape:
        await run_persist_phase(
            options,
            to_scrape=to_scrape,
            status=status,
            status_path=status_path,
            logger=logger,
        )
    else:
        logger.info("No profiles passed the follower precheck this run.")

    return build_output(
        options,
        status_path=status_path,
        total_input=len(input_usernames),
        processable=processable,
        skipped_existing=skipped_existing,
        status=status,
    )


def print_output(output: SafeOutput, *, json_output: bool) -> None:
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
        output = asyncio.run(run(options))
        print_output(output, json_output=options.json_output)
        return EXIT_SUCCESS if output.success else EXIT_RUN_FAILED
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED
    except SystemExit:
        raise
    except Exception as exc:
        if _is_config_error(exc):
            output = SafeOutput(
                success=False,
                input_path="",
                status_path=None,
                total_input=0,
                processable=0,
                skipped_existing=0,
                prechecked=0,
                passed_precheck=0,
                skipped_low_followers=0,
                not_found=0,
                precheck_failed=0,
                scraped_ok=0,
                persist_failed=0,
                min_followers=0,
                max_profiles=0,
                error=str(exc),
            )
            print_output(output, json_output=_json_requested(argv))
            return EXIT_CONFIG_ERROR
        raise


if __name__ == "__main__":
    raise SystemExit(main())
