from __future__ import annotations

import asyncio
import logging
from typing import Any

import pytest
from kiizama_scrape_core.ig_scraper_v2 import build_scraper_v2_config
from kiizama_scrape_core.ig_scraper_v2.batch_runner import (
    InstagramBatchScrapeRunner,
    normalize_usernames,
)
from kiizama_scrape_core.ig_scraper_v2.classes import (
    InstagramScrapeResult,
    InstagramSuggestedUser,
    SessionValidationResult,
)
from kiizama_scrape_core.ig_scraper_v2.schemas import InstagramBatchScrapeResponse


class FakeStore:
    async def list_credentials(self, *, limit: int) -> list[Any]:
        return []

    def decrypt_password(self, encrypted_password: str) -> str:
        return encrypted_password

    async def persist_session(self, credential_id: str, state: dict[str, Any]) -> bool:
        return True


class FakeBootstrapper:
    def __init__(self, *, result: SessionValidationResult) -> None:
        self.result = result

    async def ensure_session(self) -> SessionValidationResult:
        return self.result


class FakePage:
    def __init__(self) -> None:
        self.closed = False
        self.stealth_applied = False

    async def add_init_script(self, _script: str) -> None:
        self.stealth_applied = True

    async def set_extra_http_headers(self, _headers: dict[str, str]) -> None:
        return None

    async def close(self) -> None:
        self.closed = True


class FakeContext:
    def __init__(self) -> None:
        self.pages: list[FakePage] = []

    async def new_page(self) -> FakePage:
        page = FakePage()
        self.pages.append(page)
        return page


class FakeBrowser:
    def __init__(
        self,
        *,
        captured: dict[str, Any],
        storage_state: dict[str, Any] | None,
        credential_id: str | None,
    ) -> None:
        self.context = FakeContext()
        captured["context"] = self.context
        captured["storage_state"] = storage_state
        captured["credential_id"] = credential_id
        self.captured = captured

    async def __aenter__(self) -> FakeBrowser:
        self.captured["entered"] = True
        return self

    async def __aexit__(self, *args: Any) -> None:
        self.captured["closed"] = True

    async def retryable_goto(self, *args: Any, **kwargs: Any) -> None:
        return None


class FakeNavigator:
    pass


class FakeProfileScraper:
    def __init__(
        self,
        *,
        results_by_username: dict[str, InstagramScrapeResult],
        state: dict[str, int],
    ) -> None:
        self.results_by_username = results_by_username
        self.state = state

    async def scrape(self, _page: FakePage, username: str) -> InstagramScrapeResult:
        self.state["active"] += 1
        self.state["max_active"] = max(self.state["max_active"], self.state["active"])
        await asyncio.sleep(0)
        self.state["active"] -= 1
        return self.results_by_username[username]


async def noop_sleep(_delay: float) -> None:
    return None


def session_factory(
    *,
    success: bool = True,
    storage_state: dict[str, Any] | None = None,
    credential_id: str = "cred_1",
) -> Any:
    def factory(**_kwargs: Any) -> FakeBootstrapper:
        return FakeBootstrapper(
            result=SessionValidationResult(
                success=success,
                credential_id=credential_id if success else None,
                storage_state=storage_state,
                message="ok" if success else "no session",
                error=None if success else "no session",
            )
        )

    return factory


def scrape_result(
    *,
    username: str | None = None,
    error: str | None = None,
) -> InstagramScrapeResult:
    result = InstagramScrapeResult(success=bool(username), error=error)
    if username:
        result.user.username = username
        result.user.follower_count = 10
    return result


def scrape_result_with_recommendations() -> InstagramScrapeResult:
    result = scrape_result(username="one")
    result.recommended_users = [InstagramSuggestedUser(username="related")]
    return result


def test_normalize_usernames_filters_invalid_and_duplicates() -> None:
    assert normalize_usernames([" @One/ ", "", "one", "Two"]) == ["one", "two"]


@pytest.mark.anyio
async def test_batch_runner_uses_new_browser_and_respects_max_concurrent() -> None:
    captured: dict[str, Any] = {}
    active_state = {"active": 0, "max_active": 0}
    session_state = {"cookies": [], "__session": {"headers": {"X-IG-App-ID": "x"}}}
    results_by_username = {
        "one": scrape_result(username="one"),
        "two": scrape_result(username="two"),
        "missing": scrape_result(error="Instagram username does not exist"),
    }

    def browser_session_factory(**kwargs: Any) -> FakeBrowser:
        return FakeBrowser(
            captured=captured,
            storage_state=kwargs["storage_state"],
            credential_id=kwargs["credential_id"],
        )

    def profile_scraper_factory(**_kwargs: Any) -> FakeProfileScraper:
        return FakeProfileScraper(
            results_by_username=results_by_username,
            state=active_state,
        )

    result = await InstagramBatchScrapeRunner(
        config=build_scraper_v2_config(env={}, max_concurrent=2),
        credentials_store=FakeStore(),
        usernames=["one", "two", "missing"],
        session_bootstrapper_factory=session_factory(storage_state=session_state),
        browser_session_factory=browser_session_factory,
        navigator_factory=lambda **_kwargs: FakeNavigator(),
        profile_scraper_factory=profile_scraper_factory,
        sleeper=noop_sleep,
    ).run()

    assert result.success is False
    assert result.credential_id == "cred_1"
    assert captured["entered"] is True
    assert captured["closed"] is True
    assert captured["storage_state"] == session_state
    assert active_state["max_active"] == 2
    assert len(captured["context"].pages) == 3
    assert all(page.closed for page in captured["context"].pages)
    assert all(page.stealth_applied for page in captured["context"].pages)
    assert result.counters.requested == 3
    assert result.counters.successful == 2
    assert result.counters.failed == 0
    assert result.counters.not_found == 1
    assert result.results["one"]["metrics"]["followers"] == 10


@pytest.mark.anyio
async def test_batch_runner_serialized_metrics_do_not_duplicate_recommendations() -> (
    None
):
    def profile_scraper_factory(**_kwargs: Any) -> FakeProfileScraper:
        return FakeProfileScraper(
            results_by_username={"one": scrape_result_with_recommendations()},
            state={"active": 0, "max_active": 0},
        )

    result = await InstagramBatchScrapeRunner(
        config=build_scraper_v2_config(env={}),
        credentials_store=FakeStore(),
        usernames=["one"],
        session_bootstrapper_factory=session_factory(storage_state={}),
        browser_session_factory=lambda **kwargs: FakeBrowser(
            captured={},
            storage_state=kwargs["storage_state"],
            credential_id=kwargs["credential_id"],
        ),
        navigator_factory=lambda **_kwargs: FakeNavigator(),
        profile_scraper_factory=profile_scraper_factory,
        sleeper=noop_sleep,
    ).run()

    assert result.results["one"]["recommended_users"] == [
        {
            "username": "related",
            "id": None,
            "full_name": None,
            "profile_pic_url": None,
        }
    ]
    assert "recommended_users" not in result.results["one"]["metrics"]
    assert "user" not in result.results["one"]["metrics"]


@pytest.mark.anyio
async def test_batch_runner_can_return_batch_response_contract() -> None:
    def profile_scraper_factory(**_kwargs: Any) -> FakeProfileScraper:
        return FakeProfileScraper(
            results_by_username={"one": scrape_result_with_recommendations()},
            state={"active": 0, "max_active": 0},
        )

    response = await InstagramBatchScrapeRunner(
        config=build_scraper_v2_config(env={}),
        credentials_store=FakeStore(),
        usernames=["one"],
        session_bootstrapper_factory=session_factory(storage_state={}),
        browser_session_factory=lambda **kwargs: FakeBrowser(
            captured={},
            storage_state=kwargs["storage_state"],
            credential_id=kwargs["credential_id"],
        ),
        navigator_factory=lambda **_kwargs: FakeNavigator(),
        profile_scraper_factory=profile_scraper_factory,
        sleeper=noop_sleep,
    ).run_response()

    assert isinstance(response, InstagramBatchScrapeResponse)
    assert response.results["one"].user.username == "one"
    assert response.results["one"].recommended_users[0].username == "related"
    metrics_payload = response.results["one"].metrics.model_dump()
    assert "recommended_users" not in metrics_payload
    assert "user" not in metrics_payload


@pytest.mark.anyio
async def test_batch_runner_session_failure_does_not_open_scrape_browser() -> None:
    browser_opened = False

    def browser_session_factory(**_kwargs: Any) -> FakeBrowser:
        nonlocal browser_opened
        browser_opened = True
        raise AssertionError("browser should not open")

    result = await InstagramBatchScrapeRunner(
        config=build_scraper_v2_config(env={}),
        credentials_store=FakeStore(),
        usernames=["one", "two"],
        session_bootstrapper_factory=session_factory(success=False),
        browser_session_factory=browser_session_factory,
        sleeper=noop_sleep,
    ).run()

    assert browser_opened is False
    assert result.success is False
    assert result.counters.failed == 2
    assert set(result.results) == {"one", "two"}


@pytest.mark.anyio
async def test_batch_runner_profile_error_does_not_stop_batch() -> None:
    results_by_username = {
        "one": scrape_result(username="one"),
        "broken": scrape_result(error="boom"),
    }

    def profile_scraper_factory(**_kwargs: Any) -> FakeProfileScraper:
        return FakeProfileScraper(
            results_by_username=results_by_username,
            state={"active": 0, "max_active": 0},
        )

    result = await InstagramBatchScrapeRunner(
        config=build_scraper_v2_config(env={}, max_concurrent=1),
        credentials_store=FakeStore(),
        usernames=["one", "broken"],
        session_bootstrapper_factory=session_factory(storage_state={}),
        browser_session_factory=lambda **kwargs: FakeBrowser(
            captured={},
            storage_state=kwargs["storage_state"],
            credential_id=kwargs["credential_id"],
        ),
        navigator_factory=lambda **_kwargs: FakeNavigator(),
        profile_scraper_factory=profile_scraper_factory,
        sleeper=noop_sleep,
    ).run()

    assert result.success is False
    assert result.counters.successful == 1
    assert result.counters.failed == 1
    assert result.results["broken"]["error"] == "boom"


@pytest.mark.anyio
async def test_batch_runner_logs_final_observability_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(
        logging.INFO,
        logger="kiizama_scrape_core.ig_scraper_v2.batch_runner",
    )

    def profile_scraper_factory(**_kwargs: Any) -> FakeProfileScraper:
        return FakeProfileScraper(
            results_by_username={"one": scrape_result(username="one")},
            state={"active": 0, "max_active": 0},
        )

    result = await InstagramBatchScrapeRunner(
        config=build_scraper_v2_config(env={}),
        credentials_store=FakeStore(),
        usernames=["one"],
        session_bootstrapper_factory=session_factory(
            storage_state={},
            credential_id="019e5cc6-d98a-71f6-975d-bd164c313865",
        ),
        browser_session_factory=lambda **kwargs: FakeBrowser(
            captured={},
            storage_state=kwargs["storage_state"],
            credential_id="019e5cc6-d98a-71f6-975d-bd164c313865",
        ),
        navigator_factory=lambda **_kwargs: FakeNavigator(),
        profile_scraper_factory=profile_scraper_factory,
        sleeper=noop_sleep,
        job_id="job_abc123",
    ).run()

    assert result.success is True
    assert "IG v2 scrape run finished" in caplog.text
    assert "job_id=job_abc123" in caplog.text
    assert "proxy_mode=local" in caplog.text
    assert "requested=1 successful=1 failed=0 not_found=0" in caplog.text
    assert "019e5cc6-...-bd164c313865" in caplog.text
    assert "019e5cc6-d98a-71f6-975d-bd164c313865" not in caplog.text
