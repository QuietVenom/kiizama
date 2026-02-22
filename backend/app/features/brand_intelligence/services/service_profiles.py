from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..schemas import InfluencerMetricsSummary, InfluencerProfileDirectoryItem
from .service_utils import (
    coerce_mapping,
    normalize_string_list,
    safe_float,
    safe_int,
    safe_username,
    snapshot_is_more_recent,
    string_or_none,
)


def build_influencer_profiles_directory(
    usernames: list[str],
    profiles: Sequence[Mapping[str, Any]],
    snapshots: Sequence[Mapping[str, Any]],
) -> tuple[list[InfluencerProfileDirectoryItem], list[str]]:
    profiles_by_username = _index_profiles_by_username(profiles)
    snapshots_by_username = _index_latest_snapshots_by_username(snapshots)

    directory: list[InfluencerProfileDirectoryItem] = []
    missing_usernames: list[str] = []
    for requested_username in usernames:
        username = safe_username(requested_username) or requested_username
        has_data = username in profiles_by_username or username in snapshots_by_username
        if not has_data:
            missing_usernames.append(username)
            continue

        profile_data = profiles_by_username.get(username, {})
        snapshot_data = snapshots_by_username.get(username, {})
        snapshot_profile_data = coerce_mapping(snapshot_data.get("profile"))
        metrics_data = coerce_mapping(snapshot_data.get("metrics"))
        post_metrics = coerce_mapping(metrics_data.get("post_metrics"))
        reel_metrics = coerce_mapping(metrics_data.get("reel_metrics"))

        merged_profile = dict(snapshot_profile_data)
        merged_profile.update(profile_data)

        ai_categories = normalize_string_list(merged_profile.get("ai_categories"))
        ai_roles = normalize_string_list(merged_profile.get("ai_roles"))

        directory.append(
            InfluencerProfileDirectoryItem(
                username=username,
                full_name=string_or_none(merged_profile.get("full_name")),
                biography=string_or_none(merged_profile.get("biography")),
                is_verified=bool(merged_profile.get("is_verified")),
                profile_pic_url=string_or_none(merged_profile.get("profile_pic_url")),
                follower_count=safe_int(merged_profile.get("follower_count")),
                ai_categories=ai_categories,
                ai_roles=ai_roles,
                metrics=InfluencerMetricsSummary(
                    total_posts=safe_int(post_metrics.get("total_posts")),
                    total_comments=safe_int(post_metrics.get("total_comments")),
                    total_likes=safe_int(post_metrics.get("total_likes")),
                    avg_engagement_rate=safe_float(
                        post_metrics.get("avg_engagement_rate")
                    ),
                    hashtags_per_post=safe_float(post_metrics.get("hashtags_per_post")),
                    mentions_per_post=safe_float(post_metrics.get("mentions_per_post")),
                    total_reels=safe_int(reel_metrics.get("total_reels")),
                    total_plays=safe_int(reel_metrics.get("total_plays")),
                    overall_engagement_rate=safe_float(
                        metrics_data.get("overall_engagement_rate")
                    ),
                ),
            )
        )

    return directory, missing_usernames


def build_creator_profile_summary(
    creator_username: str,
    *,
    profiles: Sequence[Mapping[str, Any]],
    snapshots: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    normalized_username = safe_username(creator_username)
    profiles_by_username = _index_profiles_by_username(profiles)
    snapshots_by_username = _index_latest_snapshots_by_username(snapshots)

    profile_data = profiles_by_username.get(normalized_username, {})
    snapshot_data = snapshots_by_username.get(normalized_username, {})
    snapshot_profile_data = coerce_mapping(snapshot_data.get("profile"))

    merged_profile = dict(snapshot_profile_data)
    merged_profile.update(profile_data)

    metrics_data = coerce_mapping(snapshot_data.get("metrics"))
    post_metrics = coerce_mapping(metrics_data.get("post_metrics"))
    reel_metrics = coerce_mapping(metrics_data.get("reel_metrics"))
    creator_full_name = string_or_none(merged_profile.get("full_name"))
    creator_biography = string_or_none(merged_profile.get("biography"))
    creator_profile_pic_url = string_or_none(merged_profile.get("profile_pic_url"))
    creator_is_verified = bool(merged_profile.get("is_verified"))
    creator_follower_count = safe_int(merged_profile.get("follower_count"))
    creator_ai_categories = normalize_string_list(merged_profile.get("ai_categories"))
    creator_ai_roles = normalize_string_list(merged_profile.get("ai_roles"))
    current_metrics = build_creator_metrics_snapshot(
        metrics_data,
        creator_full_name=creator_full_name,
        creator_biography=creator_biography,
        creator_profile_pic_url=creator_profile_pic_url,
        creator_is_verified=creator_is_verified,
        creator_follower_count=creator_follower_count,
        creator_ai_categories=creator_ai_categories,
        creator_ai_roles=creator_ai_roles,
        post_metrics=post_metrics,
        reel_metrics=reel_metrics,
    )

    missing_creator = not merged_profile and not metrics_data
    return {
        "full_name": creator_full_name,
        "biography": creator_biography,
        "profile_pic_url": creator_profile_pic_url,
        "is_verified": creator_is_verified,
        "follower_count": creator_follower_count,
        "ai_categories": creator_ai_categories,
        "ai_roles": creator_ai_roles,
        "current_metrics": current_metrics,
        "missing_creator": missing_creator,
    }


def build_creator_metrics_snapshot(
    metrics_data: Mapping[str, Any],
    *,
    creator_full_name: str | None,
    creator_biography: str | None,
    creator_profile_pic_url: str | None,
    creator_is_verified: bool,
    creator_follower_count: int,
    creator_ai_categories: list[str],
    creator_ai_roles: list[str],
    post_metrics: Mapping[str, Any],
    reel_metrics: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "creator_full_name": creator_full_name,
        "creator_biography": creator_biography,
        "creator_profile_pic_url": creator_profile_pic_url,
        "creator_is_verified": creator_is_verified,
        "creator_follower_count": creator_follower_count,
        "creator_ai_categories": creator_ai_categories,
        "creator_ai_roles": creator_ai_roles,
        "total_likes": safe_int(post_metrics.get("total_likes")),
        "avg_engagement_rate": safe_float(post_metrics.get("avg_engagement_rate")),
        "hashtags_per_post": safe_float(post_metrics.get("hashtags_per_post")),
        "mentions_per_post": safe_float(post_metrics.get("mentions_per_post")),
        "total_reels": safe_int(reel_metrics.get("total_reels")),
        "total_plays": safe_int(reel_metrics.get("total_plays")),
        "overall_engagement_rate": safe_float(
            metrics_data.get("overall_engagement_rate")
        ),
    }


def _index_profiles_by_username(
    profiles: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    profiles_by_username: dict[str, Mapping[str, Any]] = {}
    for profile in profiles:
        profile_data = coerce_mapping(profile)
        username = safe_username(profile_data.get("username"))
        if username:
            profiles_by_username[username] = profile_data
    return profiles_by_username


def _index_latest_snapshots_by_username(
    snapshots: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    snapshots_by_username: dict[str, Mapping[str, Any]] = {}
    for snapshot in snapshots:
        snapshot_data = coerce_mapping(snapshot)
        snapshot_profile = coerce_mapping(snapshot_data.get("profile"))
        username = safe_username(snapshot_profile.get("username"))
        if not username:
            continue

        existing_snapshot = snapshots_by_username.get(username)
        if existing_snapshot is None:
            snapshots_by_username[username] = snapshot_data
            continue

        if snapshot_is_more_recent(snapshot_data, existing_snapshot):
            snapshots_by_username[username] = snapshot_data
    return snapshots_by_username


__all__ = [
    "build_influencer_profiles_directory",
    "build_creator_profile_summary",
]
