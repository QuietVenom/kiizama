from __future__ import annotations

import asyncio
import importlib
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import httpx
import pytest
from kiizama_scrape_core.ig_scraper.schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchScrapeSummaryResponse,
    InstagramBatchUsernameStatus,
)
from sqlalchemy.exc import OperationalError

from app.features.job_control import (
    JobControlUnavailableError,
    JobRuntimeHandle,
    QueuedJobMessage,
)

if TYPE_CHECKING:
    from scrape_worker.backend_client import WorkerBackendCompletionResult


REPO_ROOT = Path(__file__).resolve().parents[3]


def _ensure_repo_root_on_path() -> None:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(autouse=True)
def _configure_worker_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_repo_root_on_path()
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:55432/app_test",
    )
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SECRET_KEY_IG_CREDENTIALS", "test-secret-key-ig")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("IG_SCRAPE_WORKER_BACKEND_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("SYSTEM_ADMIN_EMAIL", "system@example.com")
    monkeypatch.setenv("SYSTEM_ADMIN_PASSWORD", "ChangeThis1!")

    _worker_modules.cache_clear()

    if "scrape_worker.config" in sys.modules:
        config_module = cast(Any, sys.modules["scrape_worker.config"])
        config_module.reset_settings_cache()


@lru_cache(maxsize=1)
def _worker_modules() -> tuple[type[Any], Any, Any]:
    _ensure_repo_root_on_path()
    backend_client_module = importlib.import_module("scrape_worker.backend_client")
    config_module = importlib.import_module("scrape_worker.config")
    worker_module = importlib.import_module("scrape_worker.worker")
    return (
        cast(type[Any], backend_client_module.WorkerBackendCompletionResult),
        config_module.get_settings,
        worker_module,
    )


def _completion_result(*, status_code: int) -> WorkerBackendCompletionResult:
    completion_result_cls, _settings, _worker_module = _worker_modules()
    return completion_result_cls(status_code=status_code)


def _settings() -> Any:
    _completion_result_cls, get_settings, _worker_module = _worker_modules()
    return get_settings()


def _attempt_exhausted(attempt: int) -> bool:
    _completion_result_cls, _settings_obj, worker_module = _worker_modules()
    return cast(bool, worker_module._attempt_exhausted(attempt))


def _worker_dependency_error_cls() -> type[Exception]:
    _completion_result_cls, _settings_obj, worker_module = _worker_modules()
    return cast(type[Exception], worker_module.WorkerDependencyUnavailableError)


def _should_ack_completion_result(result: WorkerBackendCompletionResult) -> bool:
    _completion_result_cls, _settings_obj, worker_module = _worker_modules()
    return cast(bool, worker_module._should_ack_completion_result(result))


async def _process_message(
    *,
    runtime: Any,
    backend_client: Any,
    message: QueuedJobMessage,
) -> None:
    _completion_result_cls, _settings_obj, worker_module = _worker_modules()
    await worker_module.process_message(
        runtime=runtime,
        backend_client=backend_client,
        message=message,
    )


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _summary() -> InstagramBatchScrapeSummaryResponse:
    return InstagramBatchScrapeSummaryResponse(
        usernames=[InstagramBatchUsernameStatus(username="alpha", status="success")],
        counters=InstagramBatchCountersSchema(requested=1, successful=1),
        error=None,
    )


@dataclass
class FakeRuntime:
    handle: JobRuntimeHandle
    finished: list[tuple[JobRuntimeHandle, bool]]

    def __init__(self, handle: JobRuntimeHandle) -> None:
        self.handle = handle
        self.finished = []

    async def start_job(
        self,
        message: QueuedJobMessage,
    ) -> JobRuntimeHandle | None:
        del message
        return self.handle

    async def finish_job(
        self,
        handle: JobRuntimeHandle,
        *,
        ack: bool,
        expire_state: bool = False,
    ) -> None:
        del expire_state
        self.finished.append((handle, ack))


class FakeBackendClient:
    def __init__(self, result: WorkerBackendCompletionResult) -> None:
        self.result = result
        self.calls: list[tuple[str, Any]] = []

    async def complete_job(
        self,
        *,
        job_id: str,
        payload: Any,
    ) -> WorkerBackendCompletionResult:
        self.calls.append((job_id, payload))
        return self.result

    async def aclose(self) -> None:
        return None


def _message(*, job_id: str = "job-1") -> QueuedJobMessage:
    return QueuedJobMessage(
        job_id=job_id,
        owner_user_id="user-1",
        created_at=datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
        expires_at=datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
        payload={"usernames": ["alpha"]},
        message_id="1-0",
    )


def _handle(*, attempt: int = 1) -> JobRuntimeHandle:
    return JobRuntimeHandle(
        message=_message(),
        attempt=attempt,
        lease_token="worker-1",
        started_at=datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
        lease_lost=asyncio.Event(),
    )


def test_attempt_exhausted_is_strictly_greater_than_configured_limit() -> None:
    settings = _settings()
    assert _attempt_exhausted(settings.max_attempts) is False
    assert _attempt_exhausted(settings.max_attempts + 1) is True


def test_should_ack_completion_result_only_for_terminal_backend_outcomes() -> None:
    assert _should_ack_completion_result(_completion_result(status_code=200))
    assert _should_ack_completion_result(_completion_result(status_code=409))
    assert not _should_ack_completion_result(_completion_result(status_code=503))


def test_process_message_leaves_message_pending_when_backend_completion_is_transient(
    monkeypatch: Any,
) -> None:
    runtime = FakeRuntime(_handle())
    backend_client = FakeBackendClient(_completion_result(status_code=503))

    async def fake_execute_job_payload(
        payload: dict[str, Any],
    ) -> tuple[Any, str | None]:
        del payload
        return _summary(), None

    _worker_modules()
    monkeypatch.setattr(
        "scrape_worker.worker.execute_job_payload", fake_execute_job_payload
    )

    _run(
        _process_message(
            runtime=runtime,
            backend_client=backend_client,
            message=_message(),
        )
    )

    assert len(backend_client.calls) == 1
    assert runtime.finished == [(runtime.handle, False)]


def test_process_message_acks_when_backend_reports_conflict(monkeypatch: Any) -> None:
    runtime = FakeRuntime(_handle())
    backend_client = FakeBackendClient(_completion_result(status_code=409))

    async def fake_execute_job_payload(
        payload: dict[str, Any],
    ) -> tuple[Any, str | None]:
        del payload
        return _summary(), None

    _worker_modules()
    monkeypatch.setattr(
        "scrape_worker.worker.execute_job_payload", fake_execute_job_payload
    )

    _run(
        _process_message(
            runtime=runtime,
            backend_client=backend_client,
            message=_message(),
        )
    )

    assert len(backend_client.calls) == 1
    assert runtime.finished == [(runtime.handle, True)]


def test_process_message_short_circuits_scrape_when_attempts_are_exhausted(
    monkeypatch: Any,
) -> None:
    settings = _settings()
    runtime = FakeRuntime(_handle(attempt=settings.max_attempts + 1))
    backend_client = FakeBackendClient(_completion_result(status_code=200))

    async def fake_execute_job_payload(
        payload: dict[str, Any],
    ) -> tuple[Any, str | None]:
        raise AssertionError(f"execute_job_payload should not run: {payload!r}")

    _worker_modules()
    monkeypatch.setattr(
        "scrape_worker.worker.execute_job_payload", fake_execute_job_payload
    )

    _run(
        _process_message(
            runtime=runtime,
            backend_client=backend_client,
            message=_message(),
        )
    )

    assert runtime.finished == [(runtime.handle, True)]
    assert len(backend_client.calls) == 1
    _job_id, payload = backend_client.calls[0]
    assert payload.status == "failed"
    assert payload.summary.error == "Max attempts reached before successful completion."


def test_process_message_skips_backend_completion_when_lease_is_lost(
    monkeypatch: Any,
) -> None:
    handle = _handle()
    handle.lease_lost.set()
    runtime = FakeRuntime(handle)
    backend_client = FakeBackendClient(_completion_result(status_code=200))

    async def fake_execute_job_payload(
        payload: dict[str, Any],
    ) -> tuple[Any, str | None]:
        del payload
        return _summary(), None

    _worker_modules()
    monkeypatch.setattr(
        "scrape_worker.worker.execute_job_payload", fake_execute_job_payload
    )

    _run(
        _process_message(
            runtime=runtime,
            backend_client=backend_client,
            message=_message(),
        )
    )

    assert backend_client.calls == []
    assert runtime.finished == [(runtime.handle, False)]


def test_process_message_leaves_job_pending_when_backend_transport_is_unavailable(
    monkeypatch: Any,
) -> None:
    runtime = FakeRuntime(_handle())

    class UnavailableBackendClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, Any]] = []

        async def complete_job(
            self,
            *,
            job_id: str,
            payload: Any,
        ) -> WorkerBackendCompletionResult:
            self.calls.append((job_id, payload))
            raise httpx.ConnectError("backend unavailable")

    backend_client = UnavailableBackendClient()

    async def fake_execute_job_payload(
        payload: dict[str, Any],
    ) -> tuple[Any, str | None]:
        del payload
        return _summary(), None

    _worker_modules()
    monkeypatch.setattr(
        "scrape_worker.worker.execute_job_payload", fake_execute_job_payload
    )

    with pytest.raises(_worker_dependency_error_cls()):
        _run(
            _process_message(
                runtime=runtime,
                backend_client=backend_client,
                message=_message(),
            )
        )

    assert len(backend_client.calls) == 1
    assert runtime.finished == [(runtime.handle, False)]


def test_process_message_leaves_job_pending_when_postgres_is_unavailable(
    monkeypatch: Any,
) -> None:
    runtime = FakeRuntime(_handle())
    backend_client = FakeBackendClient(_completion_result(status_code=200))

    async def fake_execute_job_payload(
        payload: dict[str, Any],
    ) -> tuple[Any, str | None]:
        raise OperationalError(
            statement="select 1",
            params=payload,
            orig=RuntimeError("postgres unavailable"),
        )

    _worker_modules()
    monkeypatch.setattr(
        "scrape_worker.worker.execute_job_payload", fake_execute_job_payload
    )

    with pytest.raises(_worker_dependency_error_cls()):
        _run(
            _process_message(
                runtime=runtime,
                backend_client=backend_client,
                message=_message(),
            )
        )

    assert backend_client.calls == []
    assert runtime.finished == [(runtime.handle, False)]


def test_worker_loop_uses_exponential_backoff_and_recovers_from_dependency_loss(
    monkeypatch: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _completion_result_cls, _settings_obj, worker_module = _worker_modules()
    caplog.set_level(logging.INFO, logger="scrape_worker")

    class FakeRedis:
        async def ping(self) -> bool:
            return True

    class FakeRuntimeLoop:
        def __init__(self) -> None:
            self.ensure_calls = 0
            self.poll_calls = 0

        async def ensure_consumer_group(self) -> None:
            self.ensure_calls += 1

        async def poll_messages(self) -> list[QueuedJobMessage]:
            self.poll_calls += 1
            if self.poll_calls == 1:
                raise JobControlUnavailableError("redis down")
            if self.poll_calls == 2:
                raise JobControlUnavailableError("redis still down")
            if self.poll_calls == 3:
                return []
            raise asyncio.CancelledError

    fake_redis = FakeRedis()
    fake_runtime = FakeRuntimeLoop()
    fake_backend_client = FakeBackendClient(_completion_result(status_code=200))
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr(
        worker_module,
        "configure_credentials_store_resolver",
        lambda resolver: None,
    )
    monkeypatch.setattr(
        worker_module,
        "get_worker_redis_client",
        lambda: fake_redis,
    )
    monkeypatch.setattr(worker_module, "ping_postgres", lambda: None)
    monkeypatch.setattr(
        worker_module,
        "JobControlRepository",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        worker_module,
        "JobWorkerRuntime",
        lambda **kwargs: fake_runtime,
    )
    monkeypatch.setattr(
        worker_module,
        "ScrapeWorkerBackendClient",
        lambda *, base_url: fake_backend_client,
    )
    monkeypatch.setattr(worker_module.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        _run(worker_module.worker_loop())

    assert sleep_calls == [_settings().poll_seconds, _settings().poll_seconds * 2]
    assert fake_runtime.ensure_calls == 1
    assert fake_runtime.poll_calls == 4
    assert "Worker entering degraded mode while polling scrape jobs." in caplog.text
    assert (
        "Worker still waiting on dependencies while polling scrape jobs." in caplog.text
    )
    assert "Worker dependencies recovered. Resuming scrape job polling." in caplog.text
