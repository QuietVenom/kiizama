from __future__ import annotations

import re
from typing import Any

import pytest
from kiizama_scrape_core.ig_scraper_v2 import build_scraper_v2_config
from kiizama_scrape_core.ig_scraper_v2.models import ProfileOpenStatus
from kiizama_scrape_core.ig_scraper_v2.profile_navigation import (
    InstagramProfileNavigator,
    build_profile_url,
    extract_username_from_profile_url,
    normalize_username,
)


class FakeLocator:
    def __init__(
        self,
        *,
        attribute_value: str | None = None,
        text: str = "",
        visible: bool = False,
    ) -> None:
        self.attribute_value = attribute_value
        self.text = text
        self.visible = visible

    @property
    def first(self) -> FakeLocator:
        return self

    def get_by_text(self, pattern: re.Pattern[str]) -> FakeLocator:
        return FakeLocator(text=self.text, visible=bool(pattern.search(self.text)))

    async def wait_for(self, **kwargs: Any) -> None:
        if not self.visible:
            raise RuntimeError("not visible")

    async def inner_text(self, **kwargs: Any) -> str:
        return self.text

    async def get_attribute(self, name: str, **kwargs: Any) -> str | None:
        return self.attribute_value


class FakePage:
    def __init__(
        self,
        *,
        url: str = "",
        main_text: str = "",
        canonical_url: str | None = None,
        og_url: str | None = None,
    ) -> None:
        self.url = url
        self.main_text = main_text
        self.canonical_url = canonical_url
        self.og_url = og_url
        self.closed = False

    def locator(self, selector: str) -> FakeLocator:
        if selector == "main":
            return FakeLocator(text=self.main_text)
        if selector == "link[rel='canonical']":
            return FakeLocator(attribute_value=self.canonical_url, visible=True)
        if selector == "meta[property='og:url']":
            return FakeLocator(attribute_value=self.og_url, visible=True)
        return FakeLocator()

    async def wait_for_load_state(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def close(self) -> None:
        self.closed = True


def build_navigator(
    *,
    next_url: str | None = None,
    calls: list[str] | None = None,
) -> InstagramProfileNavigator:
    async def fake_goto(page: FakePage, url: str, **_kwargs: Any) -> None:
        if calls is not None:
            calls.append(url)
        page.url = next_url or url

    return InstagramProfileNavigator(
        config=build_scraper_v2_config(env={}),
        retryable_goto=fake_goto,
    )


def test_normalize_username() -> None:
    assert normalize_username(" @Example.User/ ") == "example.user"
    assert normalize_username(" /// ") == ""


def test_build_profile_url() -> None:
    assert build_profile_url("example") == "https://www.instagram.com/example/"


def test_extract_username_from_profile_url() -> None:
    assert extract_username_from_profile_url("https://www.instagram.com/foo/") == "foo"
    assert extract_username_from_profile_url("https://www.instagram.com/p/abc/") is None


@pytest.mark.anyio
async def test_open_profile_navigates_direct_url_and_validates_url_identity() -> None:
    calls: list[str] = []
    page = FakePage()
    result = await build_navigator(calls=calls).open_profile(page, "@Example/")

    assert calls == ["https://www.instagram.com/example/"]
    assert result.success is True
    assert result.status == ProfileOpenStatus.SUCCESS
    assert result.matched_username == "example"


@pytest.mark.anyio
async def test_open_profile_validates_canonical_identity_when_url_has_no_username() -> (
    None
):
    page = FakePage(canonical_url="https://www.instagram.com/example/")
    result = await build_navigator(next_url="https://www.instagram.com/").open_profile(
        page,
        "example",
    )

    assert result.success is True
    assert result.matched_username == "example"


@pytest.mark.anyio
async def test_open_profile_detects_not_found() -> None:
    page = FakePage(main_text="Sorry, this page isn't available.")
    result = await build_navigator().open_profile(page, "missing")

    assert result.success is False
    assert result.status == ProfileOpenStatus.NOT_FOUND


@pytest.mark.anyio
async def test_open_profile_detects_auth_lost() -> None:
    page = FakePage()
    result = await build_navigator(
        next_url="https://www.instagram.com/accounts/login/"
    ).open_profile(page, "example")

    assert result.success is False
    assert result.status == ProfileOpenStatus.AUTH_LOST


@pytest.mark.anyio
async def test_open_profile_detects_challenge() -> None:
    page = FakePage()
    result = await build_navigator(
        next_url="https://www.instagram.com/challenge/"
    ).open_profile(page, "example")

    assert result.success is False
    assert result.status == ProfileOpenStatus.CHALLENGE


@pytest.mark.anyio
async def test_open_profile_detects_wrong_profile() -> None:
    page = FakePage()
    result = await build_navigator(
        next_url="https://www.instagram.com/other/"
    ).open_profile(page, "example")

    assert result.success is False
    assert result.status == ProfileOpenStatus.WRONG_PROFILE
    assert result.matched_username == "other"


@pytest.mark.anyio
async def test_open_profile_detects_metadata_identity_mismatch() -> None:
    page = FakePage(og_url="https://www.instagram.com/other/")
    result = await build_navigator(
        next_url="https://www.instagram.com/example/"
    ).open_profile(page, "example")

    assert result.success is False
    assert result.status == ProfileOpenStatus.WRONG_PROFILE
    assert result.matched_username == "other"
