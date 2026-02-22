from __future__ import annotations

import os
import socket
import uuid
from dataclasses import dataclass


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


def _read_int_env(var_name: str, default: int) -> int:
    raw = os.getenv(var_name)
    if raw is None or not raw.strip():
        return default

    value = int(raw)
    if value <= 0:
        raise ValueError(f"{var_name} must be greater than zero.")
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
    mongodb_url: str
    mongodb_database: str
    secret_key_ig_credentials: str
    openai_api_key: str
    poll_seconds: float
    heartbeat_seconds: float
    lease_seconds: int
    max_attempts: int
    max_error_length: int
    worker_id: str


settings = WorkerSettings(
    mongodb_url=_read_required_env(
        "IG_SCRAPE_WORKER_MONGODB_URL",
        fallback_var="MONGODB_URL",
    ),
    mongodb_database=_read_env(
        "IG_SCRAPE_WORKER_MONGODB_KIIZAMA_IG",
        fallback_var="MONGODB_KIIZAMA_IG",
    )
    or "kiizama_ig",
    secret_key_ig_credentials=_read_required_env(
        "IG_SCRAPE_WORKER_SECRET_KEY_IG_CREDENTIALS",
        fallback_var="SECRET_KEY_IG_CREDENTIALS",
    ),
    openai_api_key=_read_required_env(
        "IG_SCRAPE_WORKER_OPENAI_API_KEY",
        fallback_var="OPENAI_API_KEY",
    ),
    poll_seconds=_read_float_env("IG_SCRAPE_WORKER_POLL_SECONDS", 1.0),
    heartbeat_seconds=_read_float_env("IG_SCRAPE_WORKER_HEARTBEAT_SECONDS", 20.0),
    lease_seconds=_read_int_env("IG_SCRAPE_WORKER_LEASE_SECONDS", 900),
    max_attempts=_read_int_env("IG_SCRAPE_WORKER_MAX_ATTEMPTS", 3),
    max_error_length=_read_int_env("IG_SCRAPE_WORKER_ERROR_MAX_LEN", 4000),
    worker_id=_read_worker_id(),
)

if settings.heartbeat_seconds >= settings.lease_seconds:
    raise ValueError(
        "IG_SCRAPE_WORKER_HEARTBEAT_SECONDS must be lower than "
        "IG_SCRAPE_WORKER_LEASE_SECONDS."
    )

# Keep backend modules compatible: they expect these generic variable names.
os.environ["MONGODB_URL"] = settings.mongodb_url
os.environ["MONGODB_KIIZAMA_IG"] = settings.mongodb_database
os.environ["SECRET_KEY_IG_CREDENTIALS"] = settings.secret_key_ig_credentials
os.environ["OPENAI_API_KEY"] = settings.openai_api_key


__all__ = ["settings", "WorkerSettings"]
