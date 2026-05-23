from __future__ import annotations

import logging
from typing import Any

import pytest
from kiizama_scrape_core.ig_scraper_v2.login_flow import InstagramLoginFlow


class FakeLocator:
    def __init__(
        self,
        *,
        visible: bool = True,
        disabled: bool = False,
        aria_disabled: str | None = None,
        on_click: Any = None,
    ) -> None:
        self.visible = visible
        self.disabled = disabled
        self.aria_disabled = aria_disabled
        self.on_click = on_click
        self.pressed: list[str] = []

    @property
    def first(self) -> FakeLocator:
        return self

    async def wait_for(self, **kwargs: Any) -> None:
        if not self.visible:
            raise RuntimeError("not visible")

    async def click(self, **kwargs: Any) -> None:
        if self.on_click is not None:
            self.on_click()

    async def fill(self, value: str) -> None:
        self.pressed.clear()

    async def press(self, char: str) -> None:
        self.pressed.append(char)

    async def get_attribute(self, name: str) -> str | None:
        if name == "aria-disabled":
            return self.aria_disabled
        return None

    async def is_disabled(self) -> bool:
        return self.disabled


class FakePage:
    def __init__(
        self,
        *,
        fields_present: bool = True,
        button_disabled: bool = False,
        redirect_url: str = "https://www.instagram.com/",
    ) -> None:
        self.url = "https://www.instagram.com/accounts/login/"
        self.fields_present = fields_present
        self.username = FakeLocator()
        self.password = FakeLocator()
        self.button = FakeLocator(
            disabled=button_disabled,
            on_click=lambda: setattr(self, "url", redirect_url),
        )

    async def wait_for_selector(self, selector: str, **kwargs: Any) -> None:
        if not self.fields_present:
            raise RuntimeError("missing field")
        if "username" in selector or "email" in selector or "Email" in selector:
            return
        if "password" in selector or "Password" in selector:
            return
        if selector == "button[type='submit']":
            return
        raise RuntimeError(f"unsupported selector {selector}")

    def locator(self, selector: str) -> FakeLocator:
        if not self.fields_present and "input" in selector:
            return FakeLocator(visible=False)
        if "password" in selector or "Password" in selector:
            return self.password
        if selector == "button[type='submit']":
            return self.button
        return self.username

    def get_by_role(self, role: str, **kwargs: Any) -> FakeLocator:
        return self.button

    async def wait_for_load_state(self, *args: Any, **kwargs: Any) -> None:
        return None


async def noop_sleep(_delay: float) -> None:
    return None


async def fake_goto(page: FakePage, url: str, **_kwargs: Any) -> None:
    page.url = url


def build_flow() -> InstagramLoginFlow:
    return InstagramLoginFlow(
        timeout_ms=30_000,
        retryable_goto=fake_goto,
        sleeper=noop_sleep,
    )


@pytest.mark.anyio
async def test_login_flow_missing_credentials_returns_error() -> None:
    result = await build_flow().execute(
        FakePage(),
        login_username="",
        password="",
    )

    assert result.success is False
    assert result.error == "Missing Instagram login credentials"


@pytest.mark.anyio
async def test_login_flow_missing_fields_returns_login_failed() -> None:
    result = await build_flow().execute(
        FakePage(fields_present=False),
        login_username="ig_user",
        password="secret",
    )

    assert result.success is False
    assert result.error == "Login fields not found: username field, password field"


@pytest.mark.anyio
async def test_login_flow_disabled_button_returns_login_failed() -> None:
    result = await build_flow().execute(
        FakePage(button_disabled=True),
        login_username="ig_user",
        password="secret",
    )

    assert result.success is False
    assert result.error == "Login button not found or disabled"


@pytest.mark.anyio
async def test_login_flow_success_after_redirect() -> None:
    result = await build_flow().execute(
        FakePage(redirect_url="https://www.instagram.com/"),
        login_username="ig_user",
        password="secret",
    )

    assert result.success is True
    assert result.status == "ok"


@pytest.mark.anyio
async def test_login_flow_logs_elapsed_time_before_typing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(
        logging.INFO,
        logger="kiizama_scrape_core.ig_scraper_v2.login_flow",
    )

    result = await build_flow().execute(
        FakePage(redirect_url="https://www.instagram.com/"),
        login_username="ig_user",
        password="secret",
    )

    assert result.success is True
    assert "Starting Instagram credential typing" in caplog.text
    assert "elapsed_since_domcontentloaded_ms=" in caplog.text


@pytest.mark.anyio
async def test_login_flow_challenge_returns_challenge_status() -> None:
    result = await build_flow().execute(
        FakePage(redirect_url="https://www.instagram.com/challenge/"),
        login_username="ig_user",
        password="secret",
    )

    assert result.success is False
    assert result.status == "challenge"
