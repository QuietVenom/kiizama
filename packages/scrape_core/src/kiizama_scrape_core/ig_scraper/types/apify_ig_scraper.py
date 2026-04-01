from __future__ import annotations

import logging
from typing import Any

from apify_client import ApifyClientAsync
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from ..metrics import calculate_metrics_from_scrape

APIFY_INSTAGRAM_PROFILE_SCRAPER_ACTOR_ID = "apify/instagram-profile-scraper"
APIFY_MAX_USERNAMES = 10
NOT_FOUND_ERROR = "Instagram username does not exist"
_APIFY_MEDIA_TYPE_MAP = {
    "Image": 1,
    "Video": 2,
    "Sidecar": 8,
}


class ApifyInstagramExternalUrl(BaseModel):
    title: str | None = None
    url: str | None = None

    model_config = ConfigDict(extra="ignore")


class ApifyInstagramTaggedUser(BaseModel):
    username: str | None = None

    model_config = ConfigDict(extra="ignore")


class ApifyInstagramLatestPost(BaseModel):
    short_code: str | None = Field(
        default=None,
        validation_alias=AliasChoices("shortCode", "short_code"),
    )
    caption: str | None = None
    comments_count: int | None = Field(
        default=None,
        validation_alias=AliasChoices("commentsCount", "comments_count"),
    )
    likes_count: int | None = Field(
        default=None,
        validation_alias=AliasChoices("likesCount", "likes_count"),
    )
    tagged_users: list[ApifyInstagramTaggedUser] = Field(
        default_factory=list,
        validation_alias=AliasChoices("taggedUsers", "tagged_users"),
    )
    type: str | None = None

    model_config = ConfigDict(extra="ignore")


class ApifyInstagramRelatedProfile(BaseModel):
    username: str | None = None
    id: str | int | None = None
    full_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("fullName", "full_name"),
    )
    profile_pic_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("profilePicUrl", "profile_pic_url"),
    )

    model_config = ConfigDict(extra="ignore")


class ApifyInstagramProfileItem(BaseModel):
    id: str | int | None = None
    username: str | None = None
    full_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("fullName", "full_name"),
    )
    biography: str | None = None
    private: bool | None = None
    verified: bool | None = None
    profile_pic_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("profilePicUrl", "profile_pic_url"),
    )
    external_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("externalUrl", "external_url"),
    )
    followers_count: int | None = Field(
        default=None,
        validation_alias=AliasChoices("followersCount", "followers_count"),
    )
    follows_count: int | None = Field(
        default=None,
        validation_alias=AliasChoices("followsCount", "follows_count"),
    )
    posts_count: int | None = Field(
        default=None,
        validation_alias=AliasChoices("postsCount", "posts_count"),
    )
    external_urls: list[ApifyInstagramExternalUrl] = Field(
        default_factory=list,
        validation_alias=AliasChoices("externalUrls", "external_urls"),
    )
    business_category_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "businessCategoryName",
            "business_category_name",
        ),
    )
    latest_posts: list[ApifyInstagramLatestPost] = Field(
        default_factory=list,
        validation_alias=AliasChoices("latestPosts", "latest_posts"),
    )
    related_profiles: list[ApifyInstagramRelatedProfile] = Field(
        default_factory=list,
        validation_alias=AliasChoices("relatedProfiles", "related_profiles"),
    )

    model_config = ConfigDict(extra="ignore")

    @property
    def normalized_username(self) -> str | None:
        if not isinstance(self.username, str):
            return None
        username = self.username.strip().lower()
        return username or None

    @property
    def normalized_id(self) -> str | None:
        if self.id is None:
            return None
        profile_id = str(self.id).strip()
        return profile_id or None

    def is_not_found_item(self) -> bool:
        return self.normalized_id is None or self.normalized_username is None


class ApifyInstagramProfileScraper:
    """Fetch Instagram profiles from Apify and normalize them to our batch response."""

    def __init__(
        self,
        *,
        api_token: str,
        usernames: list[str],
        actor_id: str = APIFY_INSTAGRAM_PROFILE_SCRAPER_ACTOR_ID,
        include_about_section: bool = False,
    ) -> None:
        cleaned_token = api_token.strip()
        if not cleaned_token:
            raise ValueError("api_token is required")

        self.api_token = cleaned_token
        self.actor_id = actor_id.strip() or APIFY_INSTAGRAM_PROFILE_SCRAPER_ACTOR_ID
        self.include_about_section = include_about_section
        self.usernames = self._normalize_usernames(usernames)
        self.logger = logging.getLogger(
            "kiizama_scrape_core.ig_scraper.ApifyInstagramProfileScraper"
        )
        self._client = ApifyClientAsync(self.api_token)

    @staticmethod
    def _normalize_usernames(usernames: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()

        for raw_username in usernames:
            if not isinstance(raw_username, str):
                continue

            username = raw_username.strip().removeprefix("@").lower()
            if not username or username in seen:
                continue

            seen.add(username)
            normalized.append(username)

            if len(normalized) >= APIFY_MAX_USERNAMES:
                break

        return normalized

    async def run(self) -> dict[str, Any]:
        if not self.usernames:
            return {
                "results": {},
                "counters": {
                    "requested": 0,
                    "successful": 0,
                    "failed": 0,
                    "not_found": 0,
                },
                "error": "No usernames provided",
            }

        try:
            return await self._run_actor()
        except Exception as exc:
            self.logger.exception("Apify profile scrape failed: %s", exc)
            return {
                "results": {
                    username: self._build_failed_result(username, str(exc))
                    for username in self.usernames
                },
                "counters": {
                    "requested": len(self.usernames),
                    "successful": 0,
                    "failed": len(self.usernames),
                    "not_found": 0,
                },
                "error": str(exc),
            }

    async def _run_actor(self) -> dict[str, Any]:
        actor_client = self._client.actor(self.actor_id)
        call_result = await actor_client.call(
            run_input={
                "usernames": self.usernames,
                "includeAboutSection": self.include_about_section,
            }
        )
        if call_result is None:
            raise RuntimeError("Actor run failed.")

        dataset_id = self._resolve_dataset_id(call_result)
        if not dataset_id:
            raise RuntimeError("Actor run did not return a default dataset id.")

        list_items_result = await self._client.dataset(dataset_id).list_items()
        dataset_items = self._resolve_dataset_items(list_items_result)
        return self._build_response(dataset_items)

    @staticmethod
    def _resolve_dataset_id(call_result: Any) -> str | None:
        if isinstance(call_result, dict):
            dataset_id = call_result.get("defaultDatasetId")
        else:
            dataset_id = getattr(call_result, "default_dataset_id", None)
        return dataset_id if isinstance(dataset_id, str) and dataset_id else None

    @staticmethod
    def _resolve_dataset_items(list_items_result: Any) -> list[dict[str, Any]]:
        if isinstance(list_items_result, dict):
            items = list_items_result.get("items", [])
        else:
            items = getattr(list_items_result, "items", [])
        return [item for item in items if isinstance(item, dict)]

    def _build_response(self, dataset_items: list[dict[str, Any]]) -> dict[str, Any]:
        results: dict[str, dict[str, Any]] = {}

        for item in dataset_items:
            profile_item = ApifyInstagramProfileItem.model_validate(item)
            normalized_username = profile_item.normalized_username
            if normalized_username is None:
                continue

            if normalized_username not in self.usernames:
                continue

            if profile_item.is_not_found_item():
                results[normalized_username] = self._build_failed_result(
                    normalized_username,
                    NOT_FOUND_ERROR,
                )
                continue

            results[normalized_username] = self._build_success_result(profile_item)

        not_found_usernames = [
            username for username in self.usernames if username not in results
        ]
        for username in not_found_usernames:
            results[username] = self._build_failed_result(username, NOT_FOUND_ERROR)

        successful_count = sum(
            1 for result in results.values() if result.get("success") is True
        )
        not_found_count = sum(
            1
            for result in results.values()
            if result.get("success") is False and result.get("error") == NOT_FOUND_ERROR
        )
        failed_count = len(results) - successful_count - not_found_count

        return {
            "results": results,
            "counters": {
                "requested": len(self.usernames),
                "successful": successful_count,
                "failed": failed_count,
                "not_found": not_found_count,
            },
            "error": None,
        }

    def _build_success_result(self, item: ApifyInstagramProfileItem) -> dict[str, Any]:
        user = self._build_profile(item)
        posts = self._build_posts(item.latest_posts)
        reels: list[dict[str, Any]] = []
        recommended_users = self._build_recommended_users(item.related_profiles)
        scrape_result = {
            "user": user,
            "recommended_users": recommended_users,
            "posts": posts,
            "reels": reels,
            "success": True,
            "error": None,
            "ai_categories": [],
            "ai_roles": [],
            "ai_error": None,
        }
        scrape_result["metrics"] = calculate_metrics_from_scrape(scrape_result)
        return scrape_result

    @staticmethod
    def _build_profile(item: ApifyInstagramProfileItem) -> dict[str, Any]:
        bio_links: list[dict[str, Any]] = []
        for link in item.external_urls:
            if not isinstance(link.url, str) or not link.url.strip():
                continue
            title = link.title.strip() if isinstance(link.title, str) else ""
            bio_links.append({"title": title, "url": link.url.strip()})

        return {
            "id": item.normalized_id,
            "username": item.normalized_username,
            "full_name": (
                item.full_name.strip() if isinstance(item.full_name, str) else None
            ),
            "profile_pic_url": (
                item.profile_pic_url.strip()
                if isinstance(item.profile_pic_url, str)
                else None
            ),
            "biography": item.biography or "",
            "is_private": bool(item.private),
            "is_verified": bool(item.verified),
            "follower_count": item.followers_count,
            "following_count": item.follows_count,
            "media_count": item.posts_count,
            "external_url": (
                item.external_url.strip()
                if isinstance(item.external_url, str)
                else None
            ),
            "bio_links": bio_links,
            "category_name": (
                item.business_category_name.strip()
                if isinstance(item.business_category_name, str)
                else None
            ),
        }

    @staticmethod
    def _build_posts(raw_posts: list[ApifyInstagramLatestPost]) -> list[dict[str, Any]]:
        posts: list[dict[str, Any]] = []
        for post in raw_posts:
            code = post.short_code
            if not isinstance(code, str) or not code.strip():
                continue

            post_type = post.type
            posts.append(
                {
                    "code": code.strip(),
                    "caption_text": (
                        post.caption if isinstance(post.caption, str) else None
                    ),
                    "is_paid_partnership": None,
                    "coauthor_producers": [],
                    "comment_count": post.comments_count,
                    "like_count": post.likes_count,
                    "usertags": ApifyInstagramProfileScraper._build_post_usertags(
                        post.tagged_users
                    ),
                    "media_type": (
                        _APIFY_MEDIA_TYPE_MAP.get(post_type)
                        if isinstance(post_type, str)
                        else None
                    ),
                    "product_type": None,
                }
            )

        return posts

    @staticmethod
    def _build_post_usertags(
        raw_tagged_users: list[ApifyInstagramTaggedUser],
    ) -> list[str]:
        usernames: list[str] = []
        for tagged_user in raw_tagged_users:
            username = tagged_user.username
            if isinstance(username, str) and username.strip():
                usernames.append(username.strip().lower())
        return usernames

    @staticmethod
    def _build_recommended_users(
        raw_related_profiles: list[ApifyInstagramRelatedProfile],
    ) -> list[dict[str, Any]]:
        recommended_users: list[dict[str, Any]] = []
        for profile in raw_related_profiles:
            recommended_users.append(
                {
                    "username": (
                        profile.username.strip().lower()
                        if isinstance(profile.username, str)
                        else None
                    ),
                    "id": (str(profile.id).strip() if profile.id is not None else None),
                    "full_name": (
                        profile.full_name.strip()
                        if isinstance(profile.full_name, str)
                        else None
                    ),
                    "profile_pic_url": (
                        profile.profile_pic_url.strip()
                        if isinstance(profile.profile_pic_url, str)
                        else None
                    ),
                }
            )
        return recommended_users

    @staticmethod
    def _build_failed_result(username: str, error: str) -> dict[str, Any]:
        return {
            "user": {
                "id": None,
                "username": username,
                "full_name": None,
                "profile_pic_url": None,
                "biography": None,
                "is_private": None,
                "is_verified": None,
                "follower_count": None,
                "following_count": None,
                "media_count": None,
                "external_url": None,
                "bio_links": [],
                "category_name": None,
            },
            "recommended_users": [],
            "posts": [],
            "reels": [],
            "success": False,
            "error": error,
            "metrics": calculate_metrics_from_scrape({}),
            "ai_categories": [],
            "ai_roles": [],
            "ai_error": None,
        }

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        return None


__all__ = [
    "APIFY_INSTAGRAM_PROFILE_SCRAPER_ACTOR_ID",
    "APIFY_MAX_USERNAMES",
    "ApifyInstagramExternalUrl",
    "ApifyInstagramLatestPost",
    "ApifyInstagramProfileScraper",
    "ApifyInstagramProfileItem",
    "ApifyInstagramRelatedProfile",
    "ApifyInstagramTaggedUser",
]
