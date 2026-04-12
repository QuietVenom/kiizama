import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
from tenacity import retry, stop_after_attempt, wait_fixed

from app.api.main import api_router
from app.core.config import settings
from app.core.db import engine, ping_postgres
from app.core.redis import close_redis_client, get_redis_client
from app.core.resilience import (
    DependencyUnavailableError,
    UpstreamBadResponseError,
    UpstreamUnavailableError,
    build_dependency_error_payload,
    classify_postgres_exception,
    mark_dependency_failure,
    mark_dependency_success,
    translate_redis_exception,
)
from app.features.billing import process_pending_customer_sync_tasks_async
from app.features.creators_search_history import CreatorsSearchHistoryUnavailableError
from app.features.ig_scraper_jobs.apify_runner import ApifyInstagramJobRunner
from app.features.job_control import JobControlUnavailableError
from app.features.rate_limit import RateLimitExceededError
from app.features.user_events import UserEventsUnavailableError

logger = logging.getLogger(__name__)
APIFY_RUNNER_SUPERVISOR_RETRY_SECONDS = 5.0
STRIPE_CUSTOMER_SYNC_SUPERVISOR_RETRY_SECONDS = 5.0


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


@retry(stop=stop_after_attempt(30), wait=wait_fixed(1), reraise=True)
def ensure_postgres_connection() -> None:
    ping_postgres()


class ApifyRunnerSupervisor:
    def __init__(self, app: FastAPI) -> None:
        self._app = app
        self._runner: ApifyInstagramJobRunner | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            done, _ = await asyncio.wait({self._task}, timeout=1)
            if not done:
                self._task.cancel()
                with suppress(asyncio.CancelledError):
                    await self._task
            else:
                await self._task
            self._task = None
        if self._runner is not None:
            await self._runner.stop()
            self._runner = None

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            if not settings.IG_SCRAPER_APIFY_JOBS_ENABLED:
                return
            if not settings.APIFY_API_TOKEN or not settings.APIFY_API_TOKEN.strip():
                logger.warning(
                    "Skipping Apify job runner startup because APIFY_API_TOKEN "
                    "is not configured."
                )
                return

            try:
                redis = get_redis_client()
                await redis.ping()
                self._app.state.redis_client = redis
                runner = ApifyInstagramJobRunner()
                await runner.start()
                if not runner.is_running:
                    await runner.stop()
                    raise RuntimeError("Apify job runner loop did not stay active.")
                self._runner = runner
                mark_dependency_success(
                    "redis",
                    context="ig-scraper-apify-runner",
                    detail="Apify job runner connected to Redis.",
                )
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                mark_dependency_failure(
                    "redis",
                    context="ig-scraper-apify-runner",
                    detail="Apify job runner is waiting for Redis.",
                    status="degraded",
                    exc=exc,
                )
                logger.warning(
                    "Apify job runner startup failed. Retrying in %.1fs: %s",
                    APIFY_RUNNER_SUPERVISOR_RETRY_SECONDS,
                    exc,
                )
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=APIFY_RUNNER_SUPERVISOR_RETRY_SECONDS,
                    )
                except asyncio.TimeoutError:
                    continue


class StripeCustomerSyncSupervisor:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is None:
            return
        done, _ = await asyncio.wait({self._task}, timeout=1)
        if not done:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        else:
            await self._task
        self._task = None

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                with Session(engine) as session:
                    processed = await process_pending_customer_sync_tasks_async(
                        session=session
                    )
                if processed <= 0:
                    try:
                        await asyncio.wait_for(
                            self._stop_event.wait(),
                            timeout=settings.STRIPE_CUSTOMER_SYNC_POLL_SECONDS,
                        )
                    except asyncio.TimeoutError:
                        continue
                    return
                continue
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(
                    "Stripe customer sync supervisor failed. Retrying in %.1fs: %s",
                    STRIPE_CUSTOMER_SYNC_SUPERVISOR_RETRY_SECONDS,
                    exc,
                )
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=STRIPE_CUSTOMER_SYNC_SUPERVISOR_RETRY_SECONDS,
                    )
                except asyncio.TimeoutError:
                    continue


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    apify_runner_supervisor: ApifyRunnerSupervisor | None = None
    stripe_customer_sync_supervisor: StripeCustomerSyncSupervisor | None = None

    try:
        ensure_postgres_connection()
    except Exception as exc:
        translated = classify_postgres_exception(exc) or DependencyUnavailableError(
            dependency="postgres",
            detail="Postgres is unavailable during startup.",
        )
        mark_dependency_failure(
            "postgres",
            context="startup",
            detail=translated.detail,
            exc=exc,
        )
        raise
    mark_dependency_success(
        "postgres",
        context="startup",
        detail="Connected to Postgres database.",
    )
    logger.info("Connected to Postgres database.")

    if settings._resolved_redis_url():
        apify_runner_supervisor = ApifyRunnerSupervisor(app)
        redis = get_redis_client()
        try:
            await redis.ping()
        except Exception as exc:
            mark_dependency_failure(
                "redis",
                context="startup",
                detail="Redis is unavailable during startup.",
                status="degraded",
                exc=exc,
            )
            logger.warning(
                "Redis is unavailable during startup. Continuing in degraded mode."
            )
        else:
            mark_dependency_success(
                "redis",
                context="startup",
                detail="Connected to Redis.",
            )
            logger.info("Connected to Redis.")
            app.state.redis_client = redis
        await apify_runner_supervisor.start()
    else:
        mark_dependency_failure(
            "redis",
            context="startup",
            detail="REDIS_URL is not configured. SSE/user events will be unavailable.",
            status="degraded",
        )
        logger.warning(
            "REDIS_URL is not configured. SSE/user events will be unavailable."
        )

    # TODO: Move Stripe customer sync polling to a dedicated worker before
    # scaling web workers/replicas further. Running this supervisor inside each
    # FastAPI process increases duplicate polling overhead as the backend scales.
    stripe_customer_sync_supervisor = StripeCustomerSyncSupervisor()
    await stripe_customer_sync_supervisor.start()

    yield

    if stripe_customer_sync_supervisor is not None:
        await stripe_customer_sync_supervisor.stop()
    if apify_runner_supervisor is not None:
        await apify_runner_supervisor.stop()
    await close_redis_client()


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)


def _build_dependency_error_response(
    exc: DependencyUnavailableError | UpstreamBadResponseError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=build_dependency_error_payload(exc),
    )


def _build_rate_limit_error_response(exc: RateLimitExceededError) -> JSONResponse:
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": "Rate limit exceeded.",
            "policy": exc.policy,
            "retry_after_seconds": exc.retry_after_seconds,
        },
    )
    response.headers["Retry-After"] = str(exc.retry_after_seconds)
    response.headers["RateLimit-Limit"] = str(exc.limit)
    response.headers["RateLimit-Remaining"] = str(exc.remaining)
    response.headers["RateLimit-Reset"] = str(exc.reset_after_seconds)
    response.headers["RateLimit-Policy"] = exc.policy
    return response


@app.exception_handler(DependencyUnavailableError)
async def dependency_unavailable_exception_handler(
    _request: Request,
    exc: DependencyUnavailableError,
) -> JSONResponse:
    return _build_dependency_error_response(exc)


@app.exception_handler(UpstreamUnavailableError)
async def upstream_unavailable_exception_handler(
    _request: Request,
    exc: UpstreamUnavailableError,
) -> JSONResponse:
    return _build_dependency_error_response(exc)


@app.exception_handler(UpstreamBadResponseError)
async def upstream_bad_response_exception_handler(
    _request: Request,
    exc: UpstreamBadResponseError,
) -> JSONResponse:
    return _build_dependency_error_response(exc)


@app.exception_handler(JobControlUnavailableError)
async def job_control_unavailable_exception_handler(
    _request: Request,
    exc: JobControlUnavailableError,
) -> JSONResponse:
    translated = translate_redis_exception(exc, detail=str(exc))
    return _build_dependency_error_response(translated)


@app.exception_handler(UserEventsUnavailableError)
async def user_events_unavailable_exception_handler(
    _request: Request,
    exc: UserEventsUnavailableError,
) -> JSONResponse:
    translated = translate_redis_exception(exc, detail=str(exc))
    return _build_dependency_error_response(translated)


@app.exception_handler(CreatorsSearchHistoryUnavailableError)
async def creators_search_history_unavailable_exception_handler(
    _request: Request,
    exc: CreatorsSearchHistoryUnavailableError,
) -> JSONResponse:
    translated = translate_redis_exception(exc, detail=str(exc))
    return _build_dependency_error_response(translated)


@app.exception_handler(RateLimitExceededError)
async def rate_limit_exceeded_exception_handler(
    _request: Request,
    exc: RateLimitExceededError,
) -> JSONResponse:
    return _build_rate_limit_error_response(exc)


@app.middleware("http")
async def postgres_dependency_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    try:
        response: Response = await call_next(request)
    except SQLAlchemyError as exc:
        translated = classify_postgres_exception(exc)
        if translated is None:
            raise
        mark_dependency_failure(
            "postgres",
            context="request",
            detail=translated.detail,
            exc=exc,
        )
        return _build_dependency_error_response(translated)
    return response


# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
