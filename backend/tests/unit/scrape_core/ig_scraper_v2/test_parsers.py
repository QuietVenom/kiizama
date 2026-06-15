from __future__ import annotations

from kiizama_scrape_core.ig_scraper_v2.parsers import (
    dig,
    find_profile_user_data,
    parse_post_info,
    parse_reel_info,
    parse_user_info,
)


def test_dig_handles_dicts_and_lists() -> None:
    payload = {"a": [{"b": {"c": 3}}]}

    assert dig(payload, "a.0.b.c") == 3
    assert dig(payload, "a.1.b.c", "fallback") == "fallback"


def test_parse_user_info_maps_legacy_profile_fields() -> None:
    profile = parse_user_info(
        {
            "id": "123",
            "username": "example",
            "full_name": "Example User",
            "is_private": False,
            "is_verified": True,
            "follower_count": 10,
            "following_count": 2,
            "media_count": 4,
            "bio_links": [{"url": "https://example.com"}],
        }
    )

    assert profile.id == "123"
    assert profile.username == "example"
    assert profile.follower_count == 10
    assert profile.bio_links == [{"url": "https://example.com"}]


def test_find_profile_user_data_finds_nested_legacy_profile_payload() -> None:
    payload = {
        "require": [
            [
                "x",
                {
                    "props": {
                        "user": {
                            "username": "therock",
                            "follower_count": 400,
                        }
                    }
                },
            ]
        ]
    }

    user_data = find_profile_user_data(payload, target_username="therock")

    assert user_data is not None
    assert user_data["username"] == "therock"


def test_parse_post_info_maps_legacy_post_fields() -> None:
    post = parse_post_info(
        {
            "code": "abc",
            "caption": {"text": "hello"},
            "comment_count": 4,
            "like_count": 20,
            "taken_at_timestamp": 123456,
            "media_type": 1,
            "product_type": "feed",
            "coauthor_producers": [{"username": "coauthor"}],
            "usertags": {"in": [{"user": {"username": "tagged"}}]},
        }
    )

    assert post.code == "abc"
    assert post.caption_text == "hello"
    assert post.comment_count == 4
    assert post.like_count == 20
    assert post.coauthor_producers == ["coauthor"]
    assert post.usertags == ["tagged"]


def test_parse_reel_info_maps_legacy_reel_fields() -> None:
    reel = parse_reel_info(
        {
            "shortcode": "reel1",
            "play_count": 100,
            "comment_count": 3,
            "like_count": 9,
            "media_type": 2,
            "product_type": "clips",
        }
    )

    assert reel.code == "reel1"
    assert reel.play_count == 100
    assert reel.product_type == "clips"
