from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from .classes import (
    InstagramPost,
    InstagramProfile,
    InstagramReel,
    InstagramSuggestedUser,
)

JSONScalar = str | int | float | bool | None
JSONLike = JSONScalar | dict[str, Any] | Sequence[Any]
_PROFILE_MARKER_KEYS = {
    "biography",
    "follower_count",
    "full_name",
    "is_private",
    "media_count",
}


def dig[T](obj: JSONLike, path: str, default: T | None = None) -> T | None:
    cur: JSONLike = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            if part not in cur:
                return default
            cur = cast(JSONLike, cur[part])
        elif isinstance(cur, Sequence) and not isinstance(
            cur,
            str | bytes | bytearray,
        ):
            try:
                index = int(part)
            except ValueError:
                return default
            if not 0 <= index < len(cur):
                return default
            cur = cast(JSONLike, cur[index])
        else:
            return default
        if cur is None:
            return default
    return cast(T | None, cur)


def safe_cast_to_dict(
    obj: Any,
    default: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if default is None:
        default = {}
    return cast(dict[str, Any], obj) if isinstance(obj, dict) else default


def safe_cast_to_list(obj: Any, default: list[Any] | None = None) -> list[Any]:
    if default is None:
        default = []
    return obj if isinstance(obj, list) else default


def extract_coauthors(coauthors_data: Any) -> list[str]:
    result: list[str] = []
    if not isinstance(coauthors_data, list):
        return result
    for item in coauthors_data:
        if isinstance(item, dict):
            username = item.get("username")
            if isinstance(username, str):
                result.append(username)
    return result


def extract_usertags(usertags_data: Any) -> list[str]:
    result: list[str] = []
    if not isinstance(usertags_data, dict):
        return result
    inner = usertags_data.get("in")
    if not isinstance(inner, list):
        return result
    for tag in inner:
        if not isinstance(tag, dict):
            continue
        user_obj = tag.get("user")
        if isinstance(user_obj, dict):
            username = user_obj.get("username")
            if isinstance(username, str):
                result.append(username)
    return result


def parse_post_info(node: dict[str, Any]) -> InstagramPost:
    post = InstagramPost()
    if not node:
        return post

    code = node.get("code") or node.get("shortcode")
    if isinstance(code, str):
        post.code = code

    caption_raw = node.get("caption")
    if isinstance(caption_raw, dict):
        text_any = caption_raw.get("text")
        if isinstance(text_any, str):
            post.caption_text = text_any

    if "is_paid_partnership" in node:
        post.is_paid_partnership = node.get("is_paid_partnership")

    if "sponsor_tags" in node:
        post.sponsor_tags = node.get("sponsor_tags")

    coauthors = extract_coauthors(node.get("coauthor_producers"))
    if coauthors:
        post.coauthor_producers = coauthors

    for field in ("comment_count", "like_count"):
        value = node.get(field)
        if isinstance(value, int):
            setattr(post, field, value)

    usertags = extract_usertags(node.get("usertags"))
    if usertags:
        post.usertags = usertags

    timestamp = node.get("taken_at_timestamp")
    if isinstance(timestamp, int):
        post.timestamp = timestamp

    media_type = node.get("media_type")
    if isinstance(media_type, int):
        post.media_type = media_type

    product_type = node.get("product_type")
    if isinstance(product_type, str):
        post.product_type = product_type

    return post


def parse_reel_info(media: dict[str, Any]) -> InstagramReel:
    reel = InstagramReel()
    if not media:
        return reel

    code = media.get("code") or media.get("shortcode")
    if isinstance(code, str):
        reel.code = code

    for field in ("play_count", "comment_count", "like_count", "media_type"):
        value = media.get(field)
        if isinstance(value, int):
            setattr(reel, field, value)

    product_type = media.get("product_type")
    if isinstance(product_type, str):
        reel.product_type = product_type

    return reel


def parse_user_info(user_data: dict[str, Any]) -> InstagramProfile:
    profile = InstagramProfile()
    if not user_data:
        return profile

    mapping: tuple[tuple[str, type], ...] = (
        ("id", str),
        ("username", str),
        ("full_name", str),
        ("profile_pic_url", str),
        ("biography", str),
        ("is_private", bool),
        ("is_regulated_c18", bool),
        ("is_verified", bool),
        ("account_type", int),
        ("follower_count", int),
        ("following_count", int),
        ("media_count", int),
        ("external_url", str),
        ("category_name", str),
        ("has_guides", bool),
    )

    for field, expected in mapping:
        value = user_data.get(field)
        if isinstance(value, expected):
            setattr(profile, field, value)

    bio_links = user_data.get("bio_links")
    if isinstance(bio_links, list):
        profile.bio_links = cast(list[dict[str, Any]], bio_links)

    return profile


def find_profile_user_data(
    payload: Any,
    *,
    target_username: str | None = None,
) -> dict[str, Any] | None:
    normalized_target = target_username.strip().lower() if target_username else None
    for candidate in _iter_dicts(payload):
        if not is_profile_user_data(candidate, target_username=normalized_target):
            continue
        return candidate
    return None


def is_profile_user_data(
    candidate: dict[str, Any],
    *,
    target_username: str | None = None,
) -> bool:
    username = candidate.get("username")
    if target_username:
        if not isinstance(username, str):
            return False
        if username.strip().lower() != target_username:
            return False
    elif not isinstance(username, str):
        return False
    return any(key in candidate for key in _PROFILE_MARKER_KEYS)


def parse_suggested_users(
    users_data: list[dict[str, Any]],
) -> list[InstagramSuggestedUser]:
    result: list[InstagramSuggestedUser] = []
    for item in users_data:
        if not isinstance(item, dict):
            continue

        candidate = item
        while isinstance(candidate, dict):
            nested_candidate: dict[str, Any] | None = None
            for nested_key in ("user", "node", "profile"):
                nested = candidate.get(nested_key)
                if isinstance(nested, dict):
                    nested_candidate = nested
                    break
            if nested_candidate is None:
                break
            candidate = nested_candidate

        suggested = InstagramSuggestedUser()
        username = candidate.get("username")
        if isinstance(username, str):
            suggested.username = username

        raw_id = candidate.get("id")
        if raw_id is None:
            raw_id = candidate.get("pk")
        if isinstance(raw_id, str | int):
            suggested.id = str(raw_id)

        full_name = candidate.get("full_name")
        if isinstance(full_name, str):
            suggested.full_name = full_name

        profile_pic_url = candidate.get("profile_pic_url")
        if not isinstance(profile_pic_url, str):
            profile_pic_url = candidate.get("profile_pic_url_hd")
        if isinstance(profile_pic_url, str):
            suggested.profile_pic_url = profile_pic_url

        if any(
            getattr(suggested, attr) is not None
            for attr in ("username", "id", "full_name", "profile_pic_url")
        ):
            result.append(suggested)
    return result


def _iter_dicts(payload: Any) -> list[dict[str, Any]]:
    pending = [payload]
    result: list[dict[str, Any]] = []
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            result.append(current)
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)
    return result


def _first_value(user_data: dict[str, Any], *fields: str) -> Any:
    for field in fields:
        value = user_data.get(field)
        if value is not None:
            return value
    return None


def _first_int(
    user_data: dict[str, Any],
    *fields: str,
    nested_paths: tuple[str, ...] = (),
) -> int | None:
    for field in fields:
        value = user_data.get(field)
        if isinstance(value, int):
            return value
    for path in nested_paths:
        value = dig(user_data, path)
        if isinstance(value, int):
            return value
    return None


__all__ = [
    "dig",
    "extract_coauthors",
    "extract_usertags",
    "find_profile_user_data",
    "is_profile_user_data",
    "parse_post_info",
    "parse_reel_info",
    "parse_suggested_users",
    "parse_user_info",
    "safe_cast_to_dict",
    "safe_cast_to_list",
]
