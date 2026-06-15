from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from kiizama_scrape_core.ig_scraper_v2.scrape_collector import (
    InstagramScrapeCollector,
)


class FakeRequest:
    def __init__(self, method: str) -> None:
        self.method = method


class FakeResponse:
    def __init__(
        self,
        *,
        method: str = "POST",
        url: str = "https://www.instagram.com/graphql/query",
        status: int = 200,
        content_type: str = "application/json",
        payload: Any | None = None,
    ) -> None:
        self.request = FakeRequest(method)
        self.url = url
        self.status = status
        self.headers = {"content-type": content_type}
        self.payload = payload if payload is not None else {}
        self.json_called = False

    async def json(self) -> Any:
        self.json_called = True
        return self.payload


class FakePage:
    def __init__(self) -> None:
        self.listeners: dict[str, Any] = {}

    def on(self, event_name: str, callback: Any) -> None:
        self.listeners[event_name] = callback

    def remove_listener(self, event_name: str, callback: Any) -> None:
        if self.listeners.get(event_name) == callback:
            self.listeners.pop(event_name)


def load_fixture(name: str) -> dict[str, Any]:
    path = Path(__file__).with_name("fixtures") / name
    return json.loads(path.read_text())


@pytest.mark.anyio
async def test_collector_ignores_non_graphql_json_responses() -> None:
    collector = InstagramScrapeCollector(max_posts=3, target_username="example")
    response = FakeResponse(method="GET")

    await collector.handle_response(response)

    assert response.json_called is False
    assert collector.user_info is None


@pytest.mark.anyio
async def test_collector_captures_user_info_only_for_target_username() -> None:
    collector = InstagramScrapeCollector(max_posts=3, target_username="example")

    await collector.handle_response(
        FakeResponse(
            payload={
                "data": {
                    "user": {
                        "username": "other",
                        "follower_count": 10,
                        "is_private": False,
                    }
                }
            }
        )
    )
    assert collector.user_info is None

    await collector.handle_response(
        FakeResponse(
            payload={
                "data": {
                    "user": {
                        "username": "example",
                        "follower_count": 10,
                        "is_private": False,
                    }
                }
            }
        )
    )

    assert collector.user_info is not None
    assert collector.user_info["username"] == "example"


@pytest.mark.anyio
async def test_collector_accepts_instagram_javascript_graphql_response() -> None:
    collector = InstagramScrapeCollector(max_posts=3, target_username="example")

    await collector.handle_response(
        FakeResponse(
            url="https://www.instagram.com/api/graphql",
            content_type="text/javascript; charset=utf-8",
            payload={
                "data": {
                    "user": {
                        "username": "example",
                        "follower_count": 10,
                        "is_private": False,
                    }
                }
            },
        )
    )

    assert collector.user_info is not None
    assert collector.user_info["username"] == "example"


@pytest.mark.anyio
async def test_collector_handles_sanitized_profile_fixture_and_filters_foreign_owner() -> (
    None
):
    collector = InstagramScrapeCollector(max_posts=3, target_username="example")

    await collector.handle_response(
        FakeResponse(
            url="https://www.instagram.com/api/graphql",
            content_type="text/javascript; charset=utf-8",
            payload=load_fixture("profile_graphql_payload.json"),
        )
    )

    assert collector.user_info is not None
    assert collector.user_info["username"] == "example"
    assert [post.code for post in collector.posts] == [
        "owned_post",
        "ownerless_post",
    ]
    assert len(collector.posts) == 2
    assert collector.recommended_users[0].username == "related_one"


@pytest.mark.anyio
async def test_collector_handles_sanitized_reels_fixture() -> None:
    collector = InstagramScrapeCollector(max_posts=12, target_username="example")

    await collector.handle_response(
        FakeResponse(
            url="https://www.instagram.com/api/graphql",
            content_type="text/javascript; charset=utf-8",
            payload=load_fixture("reels_graphql_payload.json"),
        )
    )

    assert [reel.code for reel in collector.reels] == ["reel_one", "reel_two"]
    assert collector.reels_done_event.is_set()


@pytest.mark.anyio
async def test_collector_extracts_modern_posts_and_caps_max_posts() -> None:
    collector = InstagramScrapeCollector(max_posts=2, target_username="example")
    edges = [
        {
            "node": {
                "code": f"post_{index}",
                "owner": {"username": "example"},
                "like_count": index,
            }
        }
        for index in range(4)
    ]

    await collector.handle_response(
        FakeResponse(
            payload={
                "data": {
                    "user": {
                        "username": "example",
                        "follower_count": 10,
                        "is_private": False,
                    },
                    "xdt_api__v1__feed__user_timeline_graphql_connection": {
                        "edges": edges
                    },
                }
            }
        )
    )

    assert [post.code for post in collector.posts] == ["post_0", "post_1"]
    assert collector.posts_ready_event.is_set()


@pytest.mark.anyio
async def test_collector_deduplicates_posts_after_reload() -> None:
    collector = InstagramScrapeCollector(max_posts=3, target_username="example")
    payload = {
        "data": {
            "user": {
                "username": "example",
                "follower_count": 10,
                "is_private": False,
            },
            "xdt_api__v1__feed__user_timeline_graphql_connection": {
                "edges": [
                    {
                        "node": {
                            "code": "post_1",
                            "owner": {"username": "example"},
                        }
                    }
                ]
            },
        }
    }

    await collector.handle_response(FakeResponse(payload=payload))
    await collector.handle_response(FakeResponse(payload=payload))

    assert [post.code for post in collector.posts] == ["post_1"]


@pytest.mark.anyio
async def test_collector_extracts_legacy_posts() -> None:
    collector = InstagramScrapeCollector(max_posts=1, target_username="example")

    await collector.handle_response(
        FakeResponse(
            payload={
                "data": {
                    "user": {
                        "username": "example",
                        "follower_count": 10,
                        "is_private": False,
                        "edge_owner_to_timeline_media": {
                            "edges": [
                                {
                                    "node": {
                                        "shortcode": "legacy",
                                        "owner": {"username": "example"},
                                    }
                                }
                            ]
                        },
                    }
                }
            }
        )
    )

    assert [post.code for post in collector.posts] == ["legacy"]


@pytest.mark.anyio
async def test_collector_falls_back_to_legacy_timeline_when_modern_timeline_empty() -> (
    None
):
    collector = InstagramScrapeCollector(max_posts=1, target_username="example")

    await collector.handle_response(
        FakeResponse(
            payload={
                "data": {
                    "user": {
                        "username": "example",
                        "follower_count": 10,
                        "is_private": False,
                        "edge_owner_to_timeline_media": {
                            "edges": [
                                {
                                    "node": {
                                        "shortcode": "legacy_fallback",
                                        "owner": {"username": "example"},
                                    }
                                }
                            ]
                        },
                    },
                    "xdt_api__v1__feed__user_timeline_graphql_connection": {
                        "edges": []
                    },
                }
            }
        )
    )

    assert [post.code for post in collector.posts] == ["legacy_fallback"]


@pytest.mark.anyio
async def test_collector_uses_discover_chaining_candidate_as_user_info() -> None:
    collector = InstagramScrapeCollector(max_posts=1, target_username="example")

    await collector.handle_response(
        FakeResponse(
            payload={
                "data": {
                    "xdt_api__v1__discover__chaining": {
                        "users": [
                            {
                                "username": "example",
                                "follower_count": 10,
                                "is_private": False,
                            }
                        ]
                    }
                }
            }
        )
    )

    assert collector.user_info is not None
    assert collector.user_info["username"] == "example"


@pytest.mark.anyio
async def test_collector_collects_recommendations_opportunistically() -> None:
    collector = InstagramScrapeCollector(max_posts=1, target_username="example")

    await collector.handle_response(
        FakeResponse(
            payload={
                "data": {
                    "user": {
                        "username": "example",
                        "follower_count": 10,
                        "is_private": False,
                        "edge_related_profiles": {
                            "edges": [
                                {
                                    "node": {
                                        "username": "related_one",
                                        "id": "1",
                                        "full_name": "Related One",
                                        "profile_pic_url": "https://example.com/1.jpg",
                                    }
                                }
                            ]
                        },
                    }
                }
            }
        )
    )

    assert len(collector.recommended_users) == 1
    assert collector.recommended_users[0].username == "related_one"


@pytest.mark.anyio
async def test_collector_extracts_reels_and_marks_done() -> None:
    collector = InstagramScrapeCollector(max_posts=2, target_username="example")

    await collector.handle_response(
        FakeResponse(
            payload={
                "data": {
                    "xdt_api__v1__clips__user__connection_v2": {
                        "edges": [
                            {
                                "node": {
                                    "media": {
                                        "code": "reel_1",
                                        "owner": {"username": "example"},
                                        "play_count": 20,
                                    }
                                }
                            },
                            {
                                "node": {
                                    "media": {
                                        "code": "reel_2",
                                        "owner": {"username": "example"},
                                    }
                                }
                            },
                            {
                                "node": {
                                    "media": {
                                        "code": "reel_3",
                                        "owner": {"username": "example"},
                                    }
                                }
                            },
                        ]
                    }
                },
                "extensions": {"is_final": True},
            }
        )
    )

    assert [reel.code for reel in collector.reels] == ["reel_1", "reel_2"]
    assert collector.reels_done_event.is_set()


def test_collector_attach_and_detach() -> None:
    collector = InstagramScrapeCollector(max_posts=1)
    page = FakePage()

    collector.attach(page)
    assert page.listeners["response"] == collector.handle_response

    collector.detach(page)
    assert page.listeners == {}
