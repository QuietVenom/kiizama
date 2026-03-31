import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
from tenacity import retry, stop_after_attempt, wait_fixed

from app.api.main import api_router
from app.core.config import settings
from app.core.db import ping_postgres
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
from app.features.creators_search_history import CreatorsSearchHistoryUnavailableError
from app.features.job_control import JobControlUnavailableError
from app.features.rate_limit import RateLimitExceededError
from app.features.user_events import UserEventsUnavailableError

logger = logging.getLogger(__name__)


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


@retry(stop=stop_after_attempt(30), wait=wait_fixed(1), reraise=True)
def ensure_postgres_connection() -> None:
    ping_postgres()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
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

    yield

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
