import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
from tenacity import retry, stop_after_attempt, wait_fixed

from app.api.main import api_router
from app.core.config import settings
from app.core.db import ping_postgres
from app.core.mongodb import close_mongo_client, ensure_indexes, get_mongo_client

logger = logging.getLogger(__name__)


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


@retry(stop=stop_after_attempt(30), wait=wait_fixed(1), reraise=True)
def ensure_postgres_connection() -> None:
    ping_postgres()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # STARTUP (si luego necesitas inicializar algo, va aquí)
    ensure_postgres_connection()
    logger.info("Connected to Postgres database.")
    if settings.MONGODB_URL:
        client = get_mongo_client()
        database = client[settings.MONGODB_KIIZAMA_IG]
        ping_response = await database.command("ping")
        if int(ping_response.get("ok", 0)) != 1:
            raise RuntimeError("Problem connecting to database cluster.")
        logger.info("Connected to database cluster.")
        await ensure_indexes(database)
        app.state.mongodb_client = client
        app.state.mongodb_database = database
    else:
        logger.warning(
            "MONGODB_URL is not configured. Skipping MongoDB startup checks."
        )
    yield
    # SHUTDOWN
    await close_mongo_client()


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

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
