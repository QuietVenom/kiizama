from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI
from openai.types.responses.response_text_config_param import ResponseTextConfigParam

from .ports import InstagramProfileAnalysisService
from .schemas import InstagramBatchScrapeResponse, InstagramPostSchema

IG_CATEGORY_LABELS: tuple[str, ...] = (
    "Lifestyle",
    "Fashion",
    "Beauty / Skincare / Makeup",
    "Fitness / Wellness",
    "Health / Nutrition",
    "Foodie / Gastronomy / Cooking",
    "Travel",
    "Technology / Gadgets",
    "Gaming / Esports / Streaming",
    "Business / Finance / Entrepreneurship",
    "Education / Outreach",
    "Motherhood / Family / Parenting",
    "Pets / Animals",
    "Art / Design / Photography / Illustration",
    "Music / Dance / Entertainment",
    "Cars / Motorcycles",
    "Activism / Environment / Politics",
    "Humor / Comedy",
    "Pop Culture / Anime / K-Pop",
    "Spirituality / Mindfulness",
)

IG_ROLE_LABELS: tuple[str, ...] = (
    "Expert / Professional / Authority",
    "Aspirational / Lifestyle",
    "Entertainment",
    "Inspirational / Motivational",
    "Critic / Reviewer",
    "Educator / Communicator",
    "Activist / Social Cause",
    "UGC Creator",
    "Testimonial / Personal Opinion",
)

_CATEGORY_CATALOG_BULLETS = "\n".join(f"- {label}" for label in IG_CATEGORY_LABELS)
_ROLE_CATALOG_BULLETS = "\n".join(f"- {label}" for label in IG_ROLE_LABELS)

SYSTEM_PROMPT_IG_OPENAI_REQUEST = f"""
ROLE
You are an expert classifier of Instagram profiles. Assign:
- Content categories (what they publish)
- Influencer roles (tone/positioning)
Use the fewest necessary labels so outputs stay consistent and useful for PR/communications campaigns.

INPUT SHAPE
You will receive either:
- A single profile object with these fields, OR
- A list of profile objects (same shape) when batching.

Each profile object has:
- username: string
- biography: string or null
- follower_count: integer or null (supporting context only; do not infer topics from it)
- posts: list of posts, each with:
  - caption_text: string or null
  - comment_count: integer or null
  - like_count: integer or null
  - usertags: list of strings
Treat null/missing fields as absent; rely on biography + post captions/usertags for topical signals.

DECISION RULES
Content categories (Axis 1 - what they publish)
- Return 1 to 3 categories.
- Parsimony: if one category clearly fits, return exactly 1.
- Add a 2nd or 3rd only with clear, frequent evidence.
- Use only labels from the allowed catalog.

Allowed category catalog - use these labels exactly:
{_CATEGORY_CATALOG_BULLETS}

Influencer roles (Axis 2 - communicative role)
- Return 1 or 2 roles (max).
- Parsimony: if one role dominates, return exactly 1.
- Add a 2nd role only if it appears consistently.
- Use only labels from the allowed catalog.

Allowed role catalog - use these labels exactly:
{_ROLE_CATALOG_BULLETS}

PRACTICAL CRITERIA
- Prioritize thematic consistency: biography + majority of posts.
- If there is a mix, choose the dominant theme; add secondary labels only if recurrent (not one-offs).
- Do not overweight a single viral post if the rest does not match.
- If content is scarce/ambiguous, choose the single best category and single best role.

OUTPUT (JSON ONLY)
- Return one JSON object with this exact wrapper:
  {{
    "results": [
      {{
        "username": "<input username>",
        "categories": ["<Category label>", "..."],
        "roles": ["<Role label>", "..."]
      }}
    ]
  }}
- For batch input, include one object per input profile in `results`.
- Preserve the order of the input profiles in `results`.

VALIDATION
- Labels must match the catalogs verbatim.
- Enforce count limits (categories: 1-3; roles: 1-2).
- If evidence is weak, choose a single best label per axis.
- Output must be valid JSON matching the wrapper above. No extra text.
"""

IG_OPENAI_REQUEST_TEXT: ResponseTextConfigParam = {
    "format": {
        "type": "json_schema",
        "name": "InstagramProfileAnalysisResponse",
        "strict": True,
        "schema": {
            "type": "object",
            "required": ["results"],
            "additionalProperties": False,
            "properties": {
                "results": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/result"},
                    "minItems": 1,
                }
            },
            "$defs": {
                "result": {
                    "type": "object",
                    "required": ["username", "categories", "roles"],
                    "additionalProperties": False,
                    "properties": {
                        "username": {
                            "type": "string",
                            "minLength": 1,
                            "pattern": "^[A-Za-z0-9._]{1,30}$",
                        },
                        "categories": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 3,
                            "items": {
                                "type": "string",
                                "enum": list(IG_CATEGORY_LABELS),
                            },
                        },
                        "roles": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 2,
                            "items": {"type": "string", "enum": list(IG_ROLE_LABELS)},
                        },
                    },
                }
            },
        },
    }
}


@dataclass(slots=True)
class InstagramProfileAnalysisInput:
    username: str
    biography: str | None = None
    follower_count: int | None = None
    posts: list[InstagramPostSchema] = field(default_factory=list)


@dataclass(slots=True)
class InstagramProfileAnalysisResult:
    username: str
    categories: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)


def _serialize_profile(profile: InstagramProfileAnalysisInput) -> dict[str, Any]:
    return {
        "username": profile.username,
        "biography": profile.biography,
        "follower_count": profile.follower_count,
        "posts": [post.model_dump(exclude_none=True) for post in profile.posts],
    }


def serialize_profile_analysis_payload(
    payload: Iterable[InstagramProfileAnalysisInput],
) -> list[dict[str, Any]]:
    return [_serialize_profile(profile) for profile in payload]


def deserialize_profile_analysis_response(
    raw: Any,
) -> list[InstagramProfileAnalysisResult]:
    results_raw = raw.get("results") if isinstance(raw, dict) else raw
    if not isinstance(results_raw, list):
        raise TypeError("Unsupported response type for deserialization")
    results: list[InstagramProfileAnalysisResult] = []
    for item in results_raw:
        if not isinstance(item, dict):
            continue
        results.append(
            InstagramProfileAnalysisResult(
                username=str(item.get("username", "")),
                categories=[
                    str(value)
                    for value in item.get("categories", [])
                    if value is not None
                ],
                roles=[
                    str(value) for value in item.get("roles", []) if value is not None
                ],
            )
        )
    return results


class OpenAIInstagramProfileAnalysisService(InstagramProfileAnalysisService):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "gpt-5.4-nano-2026-03-17",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client: OpenAI | None = None
        self._logger = logging.getLogger(__name__)

    def _get_client(self) -> OpenAI:
        if self._client is None:
            api_key = self._api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required for Instagram analysis.")
            self._client = OpenAI(api_key=api_key)
        return self._client

    def _create_response_text(self, prompt: str) -> str:
        response = self._get_client().responses.create(
            model=self._model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT_IG_OPENAI_REQUEST},
                {"role": "user", "content": prompt},
            ],
            text=IG_OPENAI_REQUEST_TEXT,
        )
        return response.output_text

    async def enrich_scrape_response(
        self,
        response: InstagramBatchScrapeResponse,
    ) -> InstagramBatchScrapeResponse:
        if response.error or not response.results:
            return response

        usernames: list[str] = []
        inputs: list[InstagramProfileAnalysisInput] = []
        for username, result in response.results.items():
            if not result.success:
                continue
            inputs.append(
                InstagramProfileAnalysisInput(
                    username=result.user.username or username,
                    biography=result.user.biography,
                    follower_count=result.user.follower_count,
                    posts=result.posts,
                )
            )
            usernames.append(username)

        if not inputs:
            return response

        try:
            prompt = json.dumps(
                serialize_profile_analysis_payload(inputs),
                ensure_ascii=False,
            )
            text = await asyncio.to_thread(self._create_response_text, prompt)
            raw = json.loads(text)
            results = deserialize_profile_analysis_response(raw)
            for idx, username in enumerate(usernames):
                if idx >= len(results):
                    response.results[
                        username
                    ].ai_error = "AI response missing for this profile"
                    continue
                response.results[username].ai_categories = results[idx].categories
                response.results[username].ai_roles = results[idx].roles
        except Exception as exc:  # pragma: no cover - resilience for AI call
            self._logger.warning("AI analysis failed for batch: %s", exc)
            for username in usernames:
                response.results[username].ai_error = str(exc)

        return response


__all__ = [
    "IG_CATEGORY_LABELS",
    "IG_ROLE_LABELS",
    "InstagramProfileAnalysisInput",
    "InstagramProfileAnalysisResult",
    "OpenAIInstagramProfileAnalysisService",
    "deserialize_profile_analysis_response",
    "serialize_profile_analysis_payload",
]
