from __future__ import annotations

import logging
import random
from collections.abc import MutableSequence
from typing import Any

import pytest
from kiizama_scrape_core.ig_scraper_v2 import build_scraper_v2_config
from kiizama_scrape_core.ig_scraper_v2.classes import CredentialCandidate
from kiizama_scrape_core.ig_scraper_v2.login_flow import LoginFlowResult
from kiizama_scrape_core.ig_scraper_v2.session import InstagramSessionBootstrapper


class FakeStore:
    def __init__(
        self,
        credentials: list[CredentialCandidate],
        *,
        persist_result: bool = True,
    ) -> None:
        self.credentials = credentials
        self.persist_result = persist_result
        self.persist_calls: list[tuple[str, dict[str, Any]]] = []

    async def list_credentials(self, *, limit: int) -> list[CredentialCandidate]:
        return self.credentials[:limit]

    def decrypt_password(self, encrypted_password: str) -> str:
        return f"decrypted:{encrypted_password}"

    async def persist_session(self, credential_id: str, state: dict[str, Any]) -> bool:
        self.persist_calls.append((credential_id, state))
        return self.persist_result


class NoShuffleRandom(random.Random):
    def shuffle(self, x: MutableSequence[Any]) -> None:
        return None


class FakeContext:
    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state

    async def storage_state(self) -> dict[str, Any]:
        return self.state


class FakeLocator:
    def __init__(self, page: FakePage, *, kind: str) -> None:
        self.page = page
        self.kind = kind

    @property
    def first(self) -> FakeLocator:
        return self

    async def is_visible(self, **kwargs: Any) -> bool:
        return self.page.logged_in

    async def get_attribute(self, name: str) -> str | None:
        return "Settings" if self.page.logged_in else None


class FakePage:
    def __init__(self, *, session_valid: bool = False) -> None:
        self.url = ""
        self.logged_in = session_valid

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(self, kind=selector)

    def get_by_role(self, role: str, **kwargs: Any) -> FakeLocator:
        return FakeLocator(self, kind=role)

    async def wait_for_load_state(self, *args: Any, **kwargs: Any) -> None:
        return None


class FakeBrowser:
    def __init__(
        self,
        *,
        events: list[str],
        page: FakePage,
        persisted_state: dict[str, Any],
        storage_state: dict[str, Any] | None,
        extra_http_headers: dict[str, str],
        credential_id: str,
    ) -> None:
        self.events = events
        self.page = page
        self.context = FakeContext(persisted_state)
        self.storage_state = storage_state
        self.extra_http_headers = extra_http_headers
        self.credential_id = credential_id

    async def __aenter__(self) -> FakeBrowser:
        self.events.append("warmup")
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def retryable_goto(self, page: FakePage, url: str, **kwargs: Any) -> None:
        self.events.append(f"goto:{url}")
        page.url = url


class FakeLoginFlow:
    def __init__(
        self,
        *,
        page: FakePage,
        result: LoginFlowResult,
    ) -> None:
        self.page = page
        self.result = result
        self.calls: list[tuple[str, str]] = []

    async def execute(
        self,
        page: FakePage,
        *,
        login_username: str,
        password: str,
    ) -> LoginFlowResult:
        self.calls.append((login_username, password))
        if self.result.success:
            self.page.logged_in = True
        return self.result


def credential(
    *,
    session: dict[str, Any] | None = None,
) -> CredentialCandidate:
    return CredentialCandidate(
        id="cred_1",
        login_username="ig_user",
        encrypted_password="encrypted-password",
        session=session,
    )


def build_bootstrapper(
    *,
    store: FakeStore,
    page: FakePage,
    events: list[str],
    persisted_state: dict[str, Any] | None = None,
    login_result: LoginFlowResult | None = None,
) -> InstagramSessionBootstrapper:
    def browser_factory(**kwargs: Any) -> FakeBrowser:
        return FakeBrowser(
            events=events,
            page=page,
            persisted_state=persisted_state or {"cookies": [{"name": "sessionid"}]},
            storage_state=kwargs["storage_state"],
            extra_http_headers=kwargs["extra_http_headers"],
            credential_id=kwargs["credential_id"],
        )

    def login_flow_factory(**_kwargs: Any) -> FakeLoginFlow:
        return FakeLoginFlow(
            page=page,
            result=login_result
            or LoginFlowResult(success=True, status="ok", message="ok"),
        )

    return InstagramSessionBootstrapper(
        config=build_scraper_v2_config(env={}),
        credentials_store=store,
        browser_session_factory=browser_factory,
        login_flow_factory=login_flow_factory,
    )


@pytest.mark.anyio
async def test_session_bootstrapper_valid_session_avoids_login() -> None:
    events: list[str] = []
    store = FakeStore([credential(session={"cookies": []})])
    page = FakePage(session_valid=True)
    bootstrapper = build_bootstrapper(store=store, page=page, events=events)

    result = await bootstrapper.ensure_session()

    assert result.success is True
    assert result.message == "Existing Instagram session is valid"
    assert store.persist_calls
    assert events[:2] == ["warmup", "goto:https://www.instagram.com/"]


@pytest.mark.anyio
async def test_session_bootstrapper_redacts_credentials_in_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="kiizama_scrape_core.ig_scraper_v2.session")
    events: list[str] = []
    store = FakeStore(
        [
            CredentialCandidate(
                id="019e5cc6-d98a-71f6-975d-bd164c313865",
                login_username="izco.marcos@outlook.com",
                encrypted_password="encrypted-password",
                session={"cookies": []},
            )
        ]
    )
    page = FakePage(session_valid=True)
    bootstrapper = build_bootstrapper(store=store, page=page, events=events)

    result = await bootstrapper.ensure_session()

    assert result.success is True
    assert "019e5cc6-...-bd164c313865" in caplog.text
    assert "i***@outlook.com" in caplog.text
    assert "019e5cc6-d98a-71f6-975d-bd164c313865" not in caplog.text
    assert "izco.marcos@outlook.com" not in caplog.text


@pytest.mark.anyio
async def test_session_bootstrapper_passes_storage_state_and_session_headers() -> None:
    events: list[str] = []
    captured_browsers: list[FakeBrowser] = []
    store = FakeStore(
        [
            credential(
                session={
                    "cookies": [],
                    "__session": {
                        "headers": {
                            "X-IG-App-ID": "app-id",
                            "Cookie": "ignored",
                        }
                    },
                }
            )
        ]
    )
    page = FakePage(session_valid=True)

    def browser_factory(**kwargs: Any) -> FakeBrowser:
        browser = FakeBrowser(
            events=events,
            page=page,
            persisted_state={"cookies": []},
            storage_state=kwargs["storage_state"],
            extra_http_headers=kwargs["extra_http_headers"],
            credential_id=kwargs["credential_id"],
        )
        captured_browsers.append(browser)
        return browser

    bootstrapper = InstagramSessionBootstrapper(
        config=build_scraper_v2_config(env={}),
        credentials_store=store,
        browser_session_factory=browser_factory,
    )

    result = await bootstrapper.ensure_session()

    assert result.success is True
    assert captured_browsers[0].storage_state == store.credentials[0].session
    assert captured_browsers[0].extra_http_headers == {"X-IG-App-ID": "app-id"}
    assert captured_browsers[0].credential_id == "cred_1"


@pytest.mark.anyio
async def test_session_bootstrapper_invalid_session_logs_in_and_persists_new_state() -> (
    None
):
    events: list[str] = []
    persisted_state = {"cookies": [{"name": "new-session"}]}
    store = FakeStore([credential(session={"cookies": []})])
    page = FakePage(session_valid=False)
    bootstrapper = build_bootstrapper(
        store=store,
        page=page,
        events=events,
        persisted_state=persisted_state,
    )

    result = await bootstrapper.ensure_session()

    assert result.success is True
    assert result.message == "Instagram session refreshed via login"
    assert store.persist_calls == [("cred_1", persisted_state)]


@pytest.mark.anyio
async def test_session_bootstrapper_persist_failure_keeps_successful_state() -> None:
    events: list[str] = []
    persisted_state = {"cookies": [{"name": "new-session"}]}
    store = FakeStore([credential(session=None)], persist_result=False)
    page = FakePage(session_valid=False)
    bootstrapper = build_bootstrapper(
        store=store,
        page=page,
        events=events,
        persisted_state=persisted_state,
    )

    result = await bootstrapper.ensure_session()

    assert result.success is True
    assert result.storage_state == persisted_state
    assert store.persist_calls == [("cred_1", persisted_state)]


@pytest.mark.anyio
async def test_session_bootstrapper_challenge_failure_can_try_next_credential() -> None:
    events: list[str] = []
    store = FakeStore(
        [
            CredentialCandidate(
                id="cred_challenge",
                login_username="challenge",
                encrypted_password="encrypted-password",
                session=None,
            ),
            CredentialCandidate(
                id="cred_ok",
                login_username="ok",
                encrypted_password="encrypted-password",
                session=None,
            ),
        ]
    )
    page = FakePage(session_valid=False)
    calls = 0

    def browser_factory(**kwargs: Any) -> FakeBrowser:
        return FakeBrowser(
            events=events,
            page=page,
            persisted_state={"cookies": [{"name": "new-session"}]},
            storage_state=kwargs["storage_state"],
            extra_http_headers=kwargs["extra_http_headers"],
            credential_id=kwargs["credential_id"],
        )

    def login_flow_factory(**_kwargs: Any) -> FakeLoginFlow:
        nonlocal calls
        calls += 1
        if calls == 1:
            return FakeLoginFlow(
                page=page,
                result=LoginFlowResult(
                    success=False,
                    status="challenge",
                    message="Checkpoint or 2FA required",
                    error="Checkpoint or 2FA required",
                ),
            )
        return FakeLoginFlow(
            page=page,
            result=LoginFlowResult(success=True, status="ok", message="ok"),
        )

    bootstrapper = InstagramSessionBootstrapper(
        config=build_scraper_v2_config(env={}),
        credentials_store=store,
        rng=NoShuffleRandom(),
        browser_session_factory=browser_factory,
        login_flow_factory=login_flow_factory,
    )

    result = await bootstrapper.ensure_session()

    assert result.success is True
    assert result.credential_id == "cred_ok"
