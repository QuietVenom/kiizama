from __future__ import annotations

import asyncio

from fastapi import FastAPI

from app import main as backend_main


class FakeRedis:
    def __init__(self) -> None:
        self.ping_calls = 0

    async def ping(self) -> bool:
        self.ping_calls += 1
        if self.ping_calls == 1:
            raise RuntimeError("redis down")
        return True


class FakeApifyInstagramJobRunner:
    def __init__(self) -> None:
        self.is_running = False
        self.start_calls = 0
        self.stop_calls = 0

    async def start(self) -> None:
        self.start_calls += 1
        self.is_running = True

    async def stop(self) -> None:
        self.stop_calls += 1
        self.is_running = False


def test_apify_runner_supervisor_retries_until_redis_recovers(monkeypatch) -> None:
    app = FastAPI()
    redis = FakeRedis()
    created_runners: list[FakeApifyInstagramJobRunner] = []

    def fake_runner_factory() -> FakeApifyInstagramJobRunner:
        runner = FakeApifyInstagramJobRunner()
        created_runners.append(runner)
        return runner

    monkeypatch.setattr(backend_main.settings, "IG_SCRAPER_APIFY_JOBS_ENABLED", True)
    monkeypatch.setattr(backend_main.settings, "APIFY_API_TOKEN", "test-apify-token")
    monkeypatch.setattr(
        backend_main,
        "APIFY_RUNNER_SUPERVISOR_RETRY_SECONDS",
        0.01,
    )
    monkeypatch.setattr(backend_main, "get_redis_client", lambda: redis)
    monkeypatch.setattr(
        backend_main,
        "ApifyInstagramJobRunner",
        fake_runner_factory,
    )

    supervisor = backend_main.ApifyRunnerSupervisor(app)

    async def run_supervisor() -> None:
        await supervisor.start()
        await asyncio.sleep(0.05)
        await supervisor.stop()

    asyncio.run(run_supervisor())

    assert redis.ping_calls >= 2
    assert created_runners
    assert created_runners[0].start_calls == 1
    assert created_runners[0].stop_calls == 1
