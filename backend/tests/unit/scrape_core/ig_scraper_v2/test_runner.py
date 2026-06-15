from __future__ import annotations

from typing import Any

import pytest
from kiizama_scrape_core.ig_scraper_v2 import build_scraper_v2_config
from kiizama_scrape_core.ig_scraper_v2.classes import SessionValidationResult
from kiizama_scrape_core.ig_scraper_v2.models import (
    ProfileOpenResult,
    ProfileOpenStatus,
)
from kiizama_scrape_core.ig_scraper_v2.runner import InstagramProfileOpenRunner


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
        extra_http_headers: dict[str, str],
        credential_id: str | None,
    ) -> None:
        self.context = FakeContext()
        self.captured = captured
        self.captured["context"] = self.context
        self.captured["storage_state"] = storage_state
        self.captured["extra_http_headers"] = extra_http_headers
        self.captured["credential_id"] = credential_id

    async def __aenter__(self) -> FakeBrowser:
        self.captured["browser_entered"] = True
        return self

    async def __aexit__(self, *args: Any) -> None:
        self.captured["browser_closed"] = True

    async def retryable_goto(self, *args: Any, **kwargs: Any) -> None:
        return None


class FakeNavigator:
    def __init__(self, *, calls: list[str]) -> None:
        self.calls = calls

    async def open_profile(self, page: FakePage, username: str) -> ProfileOpenResult:
        self.calls.append(username)
        return ProfileOpenResult(
            requested_username=username,
            normalized_username=username.lower(),
            final_url=f"https://www.instagram.com/{username.lower()}/",
            matched_username=username.lower(),
            status=ProfileOpenStatus.SUCCESS,
            success=True,
            error=None,
        )


async def noop_sleep(_delay: float) -> None:
    return None


@pytest.mark.anyio
async def test_runner_opens_new_browser_with_fresh_storage_state() -> None:
    captured: dict[str, Any] = {}
    calls: list[str] = []
    session_state = {
        "cookies": [],
        "__session": {
            "headers": {"X-IG-App-ID": "app-id", "Cookie": "ignored"},
            "locale": "es-MX",
        },
    }

    def session_bootstrapper_factory(**_kwargs: Any) -> FakeBootstrapper:
        return FakeBootstrapper(
            result=SessionValidationResult(
                success=True,
                credential_id="cred_1",
                storage_state=session_state,
                message="ok",
            )
        )

    def browser_session_factory(**kwargs: Any) -> FakeBrowser:
        return FakeBrowser(
            captured=captured,
            storage_state=kwargs["storage_state"],
            extra_http_headers=kwargs["extra_http_headers"],
            credential_id=kwargs["credential_id"],
        )

    def navigator_factory(**_kwargs: Any) -> FakeNavigator:
        return FakeNavigator(calls=calls)

    result = await InstagramProfileOpenRunner(
        config=build_scraper_v2_config(env={}),
        credentials_store=FakeStore(),
        usernames=["One", "Two"],
        session_bootstrapper_factory=session_bootstrapper_factory,
        browser_session_factory=browser_session_factory,
        navigator_factory=navigator_factory,
        sleeper=noop_sleep,
    ).run()

    assert result.success is True
    assert result.credential_id == "cred_1"
    assert captured["browser_entered"] is True
    assert captured["browser_closed"] is True
    assert captured["storage_state"] == session_state
    assert captured["extra_http_headers"] == {"X-IG-App-ID": "app-id"}
    assert captured["credential_id"] == "cred_1"
    assert all(page.stealth_applied for page in captured["context"].pages)
    assert calls == ["One", "Two"]


@pytest.mark.anyio
async def test_runner_returns_session_failure_for_all_profiles() -> None:
    def session_bootstrapper_factory(**_kwargs: Any) -> FakeBootstrapper:
        return FakeBootstrapper(
            result=SessionValidationResult(
                success=False,
                credential_id=None,
                storage_state=None,
                message="no session",
                error="no session",
            )
        )

    result = await InstagramProfileOpenRunner(
        config=build_scraper_v2_config(env={}),
        credentials_store=FakeStore(),
        usernames=["one", "two"],
        session_bootstrapper_factory=session_bootstrapper_factory,
        sleeper=noop_sleep,
    ).run()

    assert result.success is False
    assert set(result.results) == {"one", "two"}
    assert all(
        item.status == ProfileOpenStatus.NAVIGATION_ERROR
        for item in result.results.values()
    )
