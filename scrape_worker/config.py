from __future__ import annotations

import os
import socket
import uuid
from dataclasses import dataclass
from functools import lru_cache


def _read_env(
    primary_var: str,
    *,
    fallback_var: str | None = None,
) -> str | None:
    candidates = [primary_var]
    if fallback_var:
        candidates.append(fallback_var)

    for var_name in candidates:
        raw = os.getenv(var_name)
        if raw is None:
            continue
        value = raw.strip()
        if value:
            return value
    return None


def _read_required_env(
    primary_var: str,
    *,
    fallback_var: str | None = None,
) -> str:
    value = _read_env(primary_var, fallback_var=fallback_var)
    if value is not None:
        return value

    if fallback_var:
        raise ValueError(
            f"Missing required worker config. Set {primary_var} or {fallback_var}."
        )
    raise ValueError(f"Missing required worker config. Set {primary_var}.")


def _read_float_env(var_name: str, default: float) -> float:
    raw = os.getenv(var_name)
    if raw is None or not raw.strip():
        return default

    value = float(raw)
    if value <= 0:
        raise ValueError(f"{var_name} must be greater than zero.")
    return value


def _read_numeric_env(
    primary_var: str,
    *,
    fallback_var: str | None = None,
    default: int,
) -> int:
    raw = _read_env(primary_var, fallback_var=fallback_var)
    if raw is None:
        return default

    value = int(raw)
    if value <= 0:
        raise ValueError(f"{primary_var} must be greater than zero.")
    return value


def _read_worker_id() -> str:
    raw = os.getenv("IG_SCRAPE_WORKER_ID")
    if raw and raw.strip():
        return raw.strip()

    host = socket.gethostname() or "worker"
    pid = os.getpid()
    random_suffix = uuid.uuid4().hex[:8]
    return f"{host}-{pid}-{random_suffix}"


@dataclass(frozen=True)
class WorkerSettings:
    database_url: str
    redis_url: str
    backend_base_url: str
    secret_key_ig_credentials: str
    openai_api_key: str
    system_admin_email: str
    system_admin_password: str
    poll_seconds: float
    heartbeat_seconds: float
    lease_seconds: int
    job_control_terminal_state_ttl_seconds: int
    job_control_queue_maxlen: int
    max_attempts: int
    max_error_length: int
    worker_id: str


def build_settings() -> WorkerSettings:
    settings = WorkerSettings(
        database_url=_read_required_env(
            "IG_SCRAPE_WORKER_DATABASE_URL",
            fallback_var="DATABASE_URL",
        ),
        redis_url=_read_required_env(
            "IG_SCRAPE_WORKER_REDIS_URL",
            fallback_var="REDIS_URL",
        ),
        backend_base_url=_read_required_env("IG_SCRAPE_WORKER_BACKEND_BASE_URL"),
        secret_key_ig_credentials=_read_required_env(
            "IG_SCRAPE_WORKER_SECRET_KEY_IG_CREDENTIALS",
            fallback_var="SECRET_KEY_IG_CREDENTIALS",
        ),
        openai_api_key=_read_required_env(
            "IG_SCRAPE_WORKER_OPENAI_API_KEY",
            fallback_var="OPENAI_API_KEY",
        ),
        system_admin_email=_read_required_env(
            "IG_SCRAPE_WORKER_SYSTEM_ADMIN_EMAIL",
            fallback_var="SYSTEM_ADMIN_EMAIL",
        ),
        system_admin_password=_read_required_env(
            "IG_SCRAPE_WORKER_SYSTEM_ADMIN_PASSWORD",
            fallback_var="SYSTEM_ADMIN_PASSWORD",
        ),
        poll_seconds=_read_float_env("IG_SCRAPE_WORKER_POLL_SECONDS", 1.0),
        heartbeat_seconds=_read_float_env("IG_SCRAPE_WORKER_HEARTBEAT_SECONDS", 20.0),
        lease_seconds=_read_numeric_env(
            "IG_SCRAPE_WORKER_LEASE_SECONDS",
            default=900,
        ),
        job_control_terminal_state_ttl_seconds=_read_numeric_env(
            "IG_SCRAPE_WORKER_JOB_CONTROL_TERMINAL_STATE_TTL_SECONDS",
            fallback_var="JOB_CONTROL_TERMINAL_STATE_TTL_SECONDS",
            default=60 * 60 * 24,
        ),
        job_control_queue_maxlen=_read_numeric_env(
            "IG_SCRAPE_WORKER_JOB_CONTROL_QUEUE_MAXLEN",
            fallback_var="JOB_CONTROL_QUEUE_MAXLEN",
            default=10_000,
        ),
        max_attempts=_read_numeric_env("IG_SCRAPE_WORKER_MAX_ATTEMPTS", default=3),
        max_error_length=_read_numeric_env(
            "IG_SCRAPE_WORKER_ERROR_MAX_LEN",
            default=4000,
        ),
        worker_id=_read_worker_id(),
    )

    if settings.heartbeat_seconds >= settings.lease_seconds:
        raise ValueError(
            "IG_SCRAPE_WORKER_HEARTBEAT_SECONDS must be lower than "
            "IG_SCRAPE_WORKER_LEASE_SECONDS."
        )

    return settings


@lru_cache(maxsize=1)
def get_settings() -> WorkerSettings:
    return build_settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()


__all__ = [
    "WorkerSettings",
    "build_settings",
    "get_settings",
    "reset_settings_cache",
]
