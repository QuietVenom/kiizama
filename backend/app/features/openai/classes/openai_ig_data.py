from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from app.features.ig_scrapper.schemas import InstagramPostSchema


@dataclass(slots=True)
class InstagramProfileAnalysisInput:
    """
    Minimal Instagram payload forwarded to OpenAI for categorization.

    Includes the profile basics plus the subset of post fields we care about
    (caption, comments, likes, user tags).
    """

    username: str
    biography: str | None = None
    follower_count: int | None = None
    posts: list[InstagramPostSchema] = field(default_factory=list)


@dataclass(slots=True)
class InstagramProfileAnalysisResult:
    """Expected response structure from OpenAI's Instagram analysis."""

    username: str
    categories: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)


@dataclass(slots=True)
class InstagramProfileAnalysisBatchInput:
    """Batch wrapper for sending multiple profiles in one OpenAI call."""

    profiles: list[InstagramProfileAnalysisInput] = field(default_factory=list)


@dataclass(slots=True)
class InstagramProfileAnalysisBatchResult:
    """Batch wrapper for multiple analysis results; keeps input order."""

    results: list[InstagramProfileAnalysisResult] = field(default_factory=list)


__all__ = [
    "InstagramProfileAnalysisInput",
    "InstagramProfileAnalysisResult",
    "InstagramProfileAnalysisBatchInput",
    "InstagramProfileAnalysisBatchResult",
    "serialize_profile_analysis_payload",
    "deserialize_profile_analysis_response",
]


def _serialize_profile(profile: InstagramProfileAnalysisInput) -> dict[str, Any]:
    posts = profile.posts or []
    return {
        "username": profile.username,
        "biography": profile.biography,
        "follower_count": profile.follower_count,
        "posts": [
            post.model_dump(exclude_none=True)
            if hasattr(post, "model_dump")
            else dict(post)
            for post in posts
        ],
    }


def serialize_profile_analysis_payload(
    payload: InstagramProfileAnalysisInput
    | InstagramProfileAnalysisBatchInput
    | Iterable[InstagramProfileAnalysisInput],
) -> dict[str, Any] | list[dict[str, Any]]:
    """
    Convert single or batch analysis payloads into JSON-serializable dicts/lists.
    """

    if isinstance(payload, InstagramProfileAnalysisInput):
        return _serialize_profile(payload)

    profiles: Iterable[InstagramProfileAnalysisInput]
    if isinstance(payload, InstagramProfileAnalysisBatchInput):
        profiles = payload.profiles
    elif isinstance(payload, Iterable) and not isinstance(payload, str | bytes):
        profiles = payload
    else:
        raise TypeError("Unsupported payload type for serialization")

    return [_serialize_profile(profile) for profile in profiles]


def _deserialize_result(raw: Mapping[str, Any]) -> InstagramProfileAnalysisResult:
    return InstagramProfileAnalysisResult(
        username=str(raw.get("username", "")),
        categories=[
            str(item) for item in raw.get("categories", []) if item is not None
        ],
        roles=[str(item) for item in raw.get("roles", []) if item is not None],
    )


def deserialize_profile_analysis_response(
    raw: Any,
) -> InstagramProfileAnalysisBatchResult:
    """
    Convert OpenAI JSON output into batch result wrapper.

    Supported shapes:
    - {"results": [ ...result objects... ]} (current schema)
    - {...single result object...} (legacy)
    - [...result objects...] (legacy)
    """

    if isinstance(raw, Mapping):
        wrapped_results = raw.get("results")
        if isinstance(wrapped_results, Iterable) and not isinstance(
            wrapped_results, str | bytes
        ):
            results = [
                _deserialize_result(item)
                for item in wrapped_results
                if isinstance(item, Mapping)
            ]
        else:
            results = [_deserialize_result(raw)]
    elif isinstance(raw, Iterable) and not isinstance(raw, str | bytes):
        results = [
            _deserialize_result(item) for item in raw if isinstance(item, Mapping)
        ]
    else:
        raise TypeError("Unsupported response type for deserialization")

    return InstagramProfileAnalysisBatchResult(results=results)
