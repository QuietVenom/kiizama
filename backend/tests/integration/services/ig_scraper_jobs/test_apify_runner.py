import asyncio
from types import SimpleNamespace
from typing import Any

from kiizama_scrape_core.ig_scraper.schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchProfileResult,
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeResponse,
    InstagramBatchScrapeSummaryResponse,
    InstagramBatchUsernameStatus,
    InstagramProfileSchema,
)
from redis.exceptions import RedisError

from app.features.ig_scraper_jobs import apify_runner as runner_module


class _FakeJobControlRepository:
    def __init__(self) -> None:
        self.spec = object()


class _FakeSessionContext:
    def __init__(self, session: object) -> None:
        self._session = session

    def __enter__(self) -> object:
        return self._session

    def __exit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False


class _RecordingInstagramJobService:
    created_kwargs: dict[str, Any] | None = None
    completed_job_id: str | None = None

    def __init__(self, **kwargs: Any) -> None:
        self.__class__.created_kwargs = kwargs

    async def complete_job(self, *, job_id: str, payload: Any) -> None:
        del payload
        self.__class__.completed_job_id = job_id


class _FakeApifyRuntime:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.ensure_calls = 0
        self.finish_calls: list[tuple[Any, bool]] = []
        self.start_result: Any = None

    async def ensure_consumer_group(self) -> None:
        self.ensure_calls += 1

    async def start_job(self, message: Any) -> Any:
        del message
        return self.start_result

    async def finish_job(self, handle: Any, *, ack: bool) -> None:
        self.finish_calls.append((handle, ack))


class _FakeJobHandle:
    def __init__(
        self,
        *,
        attempt: int = 1,
        payload: dict[str, Any] | None = None,
        lease_lost: bool = False,
    ) -> None:
        self.job_id = "job-123"
        self.attempt = attempt
        self.message = SimpleNamespace(payload=payload or {"usernames": ["alpha"]})
        self.lease_lost = asyncio.Event()
        if lease_lost:
            self.lease_lost.set()


def _summary(
    *,
    username: str = "alpha",
    status: str = "success",
    error: str | None = None,
) -> InstagramBatchScrapeSummaryResponse:
    counters = (
        InstagramBatchCountersSchema(requested=1, successful=1)
        if status == "success"
        else InstagramBatchCountersSchema(requested=1, failed=1)
    )
    return InstagramBatchScrapeSummaryResponse(
        usernames=[
            InstagramBatchUsernameStatus(
                username=username,
                status=status,
                error=error,
            )
        ],
        counters=counters,
        error=error,
    )


def test_apify_runner_start_is_idempotent(monkeypatch) -> None:
    runtimes: list[_FakeApifyRuntime] = []

    def fake_runtime_factory(**kwargs: Any) -> _FakeApifyRuntime:
        runtime = _FakeApifyRuntime(**kwargs)
        runtimes.append(runtime)
        return runtime

    async def idle_run_loop() -> None:
        await asyncio.Event().wait()

    async def run() -> None:
        # Arrange
        monkeypatch.setattr(runner_module, "JobWorkerRuntime", fake_runtime_factory)
        monkeypatch.setattr(
            runner_module,
            "configure_backend_instagram_scraper_runtime",
            lambda: None,
        )
        runner = runner_module.ApifyInstagramJobRunner()
        runner._run_loop = idle_run_loop

        # Act
        await runner.start()
        await runner.start()
        await runner.stop()

        # Assert
        assert len(runtimes) == 1
        assert runtimes[0].ensure_calls == 1

    asyncio.run(run())


def test_apify_runner_start_surfaces_loop_startup_failure(monkeypatch) -> None:
    async def failing_run_loop() -> None:
        raise RuntimeError("loop failed")

    async def run() -> None:
        # Arrange
        monkeypatch.setattr(
            runner_module,
            "JobWorkerRuntime",
            lambda **kwargs: _FakeApifyRuntime(**kwargs),
        )
        monkeypatch.setattr(
            runner_module,
            "configure_backend_instagram_scraper_runtime",
            lambda: None,
        )
        runner = runner_module.ApifyInstagramJobRunner()
        runner._run_loop = failing_run_loop

        # Act / Assert
        try:
            await runner.start()
        except RuntimeError as exc:
            assert str(exc) == "loop failed"
        else:  # pragma: no cover - explicit failure path
            raise AssertionError("runner.start() did not surface loop failure")

    asyncio.run(run())


def test_apify_runner_stop_cancels_loop_and_job_tasks() -> None:
    async def run() -> None:
        # Arrange
        runner = runner_module.ApifyInstagramJobRunner()
        runner._loop_task = asyncio.create_task(asyncio.sleep(60))
        job_task = asyncio.create_task(asyncio.sleep(60))
        runner._job_tasks = {job_task}

        # Act
        await runner.stop()

        # Assert
        assert runner._stop_event.is_set()
        assert runner._loop_task.done()
        assert job_task.done()
        assert runner._loop_task.cancelled()
        assert job_task.cancelled()

    asyncio.run(run())


def test_apify_runner_run_loop_releases_semaphore_when_no_messages() -> None:
    async def run() -> None:
        # Arrange
        runner = runner_module.ApifyInstagramJobRunner()
        runner._semaphore = asyncio.Semaphore(1)

        class RuntimeWithoutMessages:
            async def poll_messages(self) -> list[Any]:
                runner._stop_event.set()
                return []

        runner._runtime = RuntimeWithoutMessages()

        # Act
        await runner._run_loop()

        # Assert
        assert runner._semaphore._value == 1
        assert runner._job_tasks == set()

    asyncio.run(run())


def test_apify_runner_run_loop_backs_off_on_dependency_error(monkeypatch) -> None:
    async def run() -> None:
        # Arrange
        sleeps: list[float] = []
        runner = runner_module.ApifyInstagramJobRunner()
        runner._semaphore = asyncio.Semaphore(1)

        class FailingRuntime:
            async def poll_messages(self) -> list[Any]:
                raise RedisError("redis down")

        async def fake_sleep(seconds: float) -> None:
            sleeps.append(seconds)
            runner._stop_event.set()

        runner._runtime = FailingRuntime()
        monkeypatch.setattr(runner_module.asyncio, "sleep", fake_sleep)

        # Act
        await runner._run_loop()

        # Assert
        assert runner._semaphore._value == 1
        assert sleeps == [runner_module.settings.IG_SCRAPER_APIFY_POLL_SECONDS]

    asyncio.run(run())


def test_apify_runner_process_message_ignores_missing_handle() -> None:
    async def run() -> None:
        # Arrange
        runner = runner_module.ApifyInstagramJobRunner()
        runtime = _FakeApifyRuntime()
        runtime.start_result = None
        runner._runtime = runtime

        # Act
        await runner._process_message(SimpleNamespace())

        # Assert
        assert runtime.finish_calls == []

    asyncio.run(run())


def test_apify_runner_process_message_retries_non_terminal_failure_without_ack(
    monkeypatch,
) -> None:
    async def run() -> None:
        # Arrange
        runner = runner_module.ApifyInstagramJobRunner()
        runtime = _FakeApifyRuntime()
        handle = _FakeJobHandle(attempt=1)
        runtime.start_result = handle
        runner._runtime = runtime
        monkeypatch.setattr(
            runner_module.settings,
            "IG_SCRAPER_APIFY_MAX_ATTEMPTS",
            2,
        )

        async def failing_execute(payload: dict[str, Any]) -> tuple[Any, str | None]:
            del payload
            raise RuntimeError("temporary upstream failure")

        runner._execute_job_payload = failing_execute

        # Act
        await runner._process_message(SimpleNamespace())

        # Assert
        assert runtime.finish_calls == [(handle, False)]

    asyncio.run(run())


def test_apify_runner_process_message_terminal_failure_builds_summary_and_completes(
    monkeypatch,
) -> None:
    async def run() -> None:
        # Arrange
        completions: list[dict[str, Any]] = []
        runner = runner_module.ApifyInstagramJobRunner()
        runtime = _FakeApifyRuntime()
        handle = _FakeJobHandle(attempt=1)
        runtime.start_result = handle
        runner._runtime = runtime
        monkeypatch.setattr(
            runner_module.settings,
            "IG_SCRAPER_APIFY_MAX_ATTEMPTS",
            1,
        )

        async def failing_execute(payload: dict[str, Any]) -> tuple[Any, str | None]:
            del payload
            raise RuntimeError("terminal upstream failure")

        async def terminal_summary(
            payload: dict[str, Any],
            *,
            error: str,
        ) -> InstagramBatchScrapeSummaryResponse:
            del payload
            return _summary(status="failed", error=error)

        async def complete_job(**kwargs: Any) -> bool:
            completions.append(kwargs)
            return True

        runner._execute_job_payload = failing_execute
        runner._build_terminal_failure_summary = terminal_summary
        runner._complete_job = complete_job

        # Act
        await runner._process_message(SimpleNamespace())

        # Assert
        assert runtime.finish_calls == [(handle, True)]
        assert completions[0]["job_id"] == "job-123"
        assert completions[0]["status"] == "failed"
        assert completions[0]["summary"].counters.failed == 1
        assert completions[0]["error"] == "terminal upstream failure"

    asyncio.run(run())


def test_apify_runner_process_message_skips_completion_when_lease_lost() -> None:
    async def run() -> None:
        # Arrange
        completions: list[dict[str, Any]] = []
        runner = runner_module.ApifyInstagramJobRunner()
        runtime = _FakeApifyRuntime()
        handle = _FakeJobHandle(lease_lost=True)
        runtime.start_result = handle
        runner._runtime = runtime

        async def execute(payload: dict[str, Any]) -> tuple[Any, str | None]:
            del payload
            return _summary(), None

        async def complete_job(**kwargs: Any) -> bool:
            completions.append(kwargs)
            return True

        runner._execute_job_payload = execute
        runner._complete_job = complete_job

        # Act
        await runner._process_message(SimpleNamespace())

        # Assert
        assert completions == []
        assert runtime.finish_calls == [(handle, False)]

    asyncio.run(run())


def test_apify_runner_scrape_profiles_batch_requires_apify_token(monkeypatch) -> None:
    async def run() -> None:
        # Arrange
        monkeypatch.setattr(runner_module.settings, "APIFY_API_TOKEN", None)
        runner = runner_module.ApifyInstagramJobRunner()

        # Act / Assert
        try:
            await runner._scrape_profiles_batch(
                InstagramBatchScrapeRequest(usernames=["alpha"])
            )
        except RuntimeError as exc:
            assert str(exc) == "APIFY_API_TOKEN is not configured."
        else:  # pragma: no cover - explicit failure path
            raise AssertionError(
                "_scrape_profiles_batch() did not reject missing token"
            )

    asyncio.run(run())


def test_apify_runner_terminal_failure_summary_uses_early_response_or_exhausted_fallback(
    monkeypatch,
) -> None:
    fake_session = object()

    async def run() -> None:
        # Arrange
        runner = runner_module.ApifyInstagramJobRunner()
        early_response = InstagramBatchScrapeResponse(
            results={
                "alpha": InstagramBatchProfileResult(
                    user=InstagramProfileSchema(username="alpha"),
                    success=False,
                    error="cached failure",
                )
            },
            counters=InstagramBatchCountersSchema(requested=1, failed=1),
            error="cached failure",
        )

        async def prepare_with_early_response(
            request: InstagramBatchScrapeRequest,
            persistence: Any,
        ) -> tuple[InstagramBatchScrapeRequest, InstagramBatchScrapeResponse]:
            del persistence
            return request, early_response

        monkeypatch.setattr(
            runner_module,
            "Session",
            lambda _engine: _FakeSessionContext(fake_session),
        )
        monkeypatch.setattr(
            runner_module,
            "SqlInstagramScrapePersistence",
            lambda *, session: {"session": session},
        )
        monkeypatch.setattr(
            runner_module,
            "prepare_scrape_batch_payload",
            prepare_with_early_response,
        )

        # Act
        early_summary = await runner._build_terminal_failure_summary(
            {"usernames": ["alpha"]},
            error="terminal failure",
        )

        async def failing_prepare(
            request: InstagramBatchScrapeRequest,
            persistence: Any,
        ) -> tuple[InstagramBatchScrapeRequest, None]:
            del request, persistence
            raise RuntimeError("db unavailable")

        monkeypatch.setattr(
            runner_module,
            "prepare_scrape_batch_payload",
            failing_prepare,
        )
        exhausted_summary = await runner._build_terminal_failure_summary(
            {"usernames": ["beta"]},
            error="terminal failure",
        )

        # Assert
        assert early_summary.error == "terminal failure"
        assert early_summary.counters.failed == 1
        assert exhausted_summary.error == "terminal failure"
        assert exhausted_summary.usernames[0].username == "beta"
        assert exhausted_summary.usernames[0].status == "failed"
        assert exhausted_summary.counters.failed == 1

    asyncio.run(run())


def test_apify_runner_complete_job_passes_session_to_instagram_job_service(
    monkeypatch,
) -> None:
    fake_session = object()
    monkeypatch.setattr(
        runner_module,
        "Session",
        lambda _engine: _FakeSessionContext(fake_session),
    )
    monkeypatch.setattr(
        runner_module,
        "InstagramJobService",
        _RecordingInstagramJobService,
    )
    monkeypatch.setattr(
        runner_module,
        "SqlJobProjectionRepository",
        lambda *, session: {"session": session},
    )
    monkeypatch.setattr(
        runner_module,
        "get_instagram_apify_job_control_repository",
        lambda: _FakeJobControlRepository(),
    )
    monkeypatch.setattr(
        runner_module,
        "get_instagram_job_control_repository",
        lambda: "worker-repo",
    )
    monkeypatch.setattr(
        runner_module,
        "get_instagram_user_events_repository",
        lambda: "user-events-repo",
    )

    runner = runner_module.ApifyInstagramJobRunner()
    summary = InstagramBatchScrapeSummaryResponse(
        usernames=[InstagramBatchUsernameStatus(username="alpha", status="success")],
        counters=InstagramBatchCountersSchema(requested=1, successful=1),
        error=None,
    )

    ack = asyncio.run(
        runner._complete_job(
            job_id="job-123",
            attempt=1,
            status="done",
            summary=summary,
            error=None,
        )
    )

    assert ack is True
    assert _RecordingInstagramJobService.created_kwargs is not None
    assert _RecordingInstagramJobService.created_kwargs["session"] is fake_session
    assert (
        _RecordingInstagramJobService.created_kwargs["job_control_repositories"][
            "worker"
        ]
        == "worker-repo"
    )
    assert isinstance(
        _RecordingInstagramJobService.created_kwargs["job_control_repositories"][
            "apify"
        ],
        _FakeJobControlRepository,
    )
    assert _RecordingInstagramJobService.completed_job_id == "job-123"
