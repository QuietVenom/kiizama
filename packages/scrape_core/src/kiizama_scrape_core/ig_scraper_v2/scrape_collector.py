from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, cast

from playwright.async_api import Page, Response

from .classes import (
    InstagramPost,
    InstagramReel,
    InstagramSuggestedUser,
)
from .parsers import (
    parse_post_info,
    parse_reel_info,
    parse_suggested_users,
    safe_cast_to_dict,
    safe_cast_to_list,
)


class InstagramScrapeCollector:
    """Collect per-profile Instagram GraphQL data from Playwright responses."""

    def __init__(
        self,
        *,
        max_posts: int,
        target_username: str | None = None,
        logger: logging.Logger | None = None,
        collect_posts: bool = True,
        collect_reels: bool = True,
        collect_recommendations: bool = True,
        recommended_limit: int | None = 10,
    ) -> None:
        self.max_posts = max_posts
        self.target_username = (
            target_username.strip().lower() if target_username else None
        )
        self.logger = logger or logging.getLogger(
            "kiizama_scrape_core.ig_scraper_v2.scrape_collector"
        )
        self.collect_posts = collect_posts
        self.collect_reels = collect_reels
        self.collect_recommendations = collect_recommendations
        self.recommended_limit = recommended_limit

        self.posts_ready_event: asyncio.Event = asyncio.Event()
        self.reels_done_event: asyncio.Event = asyncio.Event()

        self.posts: list[InstagramPost] = []
        self.reels: list[InstagramReel] = []
        self.recommended_users: list[InstagramSuggestedUser] = []
        self.user_info: dict[str, Any] | None = None
        self._post_codes: set[str] = set()
        self._reel_codes: set[str] = set()
        self._recommended_user_keys: set[str] = set()

    async def handle_response(self, response: Response) -> None:
        try:
            needs_posts = self.collect_posts and not self.posts_ready_event.is_set()
            needs_reels = self.collect_reels and not self.reels_done_event.is_set()
            needs_recommendations = self.collect_recommendations and (
                self.recommended_limit is None
                or len(self.recommended_users) < self.recommended_limit
            )
            if not (needs_posts or needs_reels or needs_recommendations):
                return
            if not _is_graphql_json_response(response):
                return

            data = await response.json()
            if not isinstance(data, dict):
                return

            payload_dict = safe_cast_to_dict(data.get("data"), {})
            extensions = safe_cast_to_dict(data.get("extensions"), {})
            is_final = bool(extensions.get("is_final"))
            self._maybe_collect_user_info(payload_dict)

            if needs_posts:
                self._collect_posts(payload_dict)

            if needs_recommendations:
                self._collect_recommendations(payload_dict)

            if (
                needs_reels
                and "xdt_api__v1__clips__user__connection_v2" in payload_dict
            ):
                self._collect_reels(payload_dict, is_final=is_final)

            self._mark_ready_events()
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            self.logger.warning("Failed to parse GraphQL response: %s", exc)
        except Exception as exc:
            self.logger.error("Unexpected error processing GraphQL response: %s", exc)

    def attach(self, page: Page) -> None:
        page.on("response", self.handle_response)

    def detach(self, page: Page) -> None:
        try:
            page.remove_listener("response", self.handle_response)
        except Exception as exc:
            self.logger.warning("Failed to remove response listener: %s", exc)

    def _matches_target(self, candidate: dict[str, Any]) -> bool:
        if not self.target_username:
            return True
        username = candidate.get("username")
        return (
            isinstance(username, str)
            and username.strip().lower() == self.target_username
        )

    def _maybe_collect_user_info(self, payload_dict: dict[str, Any]) -> None:
        user_data: dict[str, Any] | None = None
        user_raw = payload_dict.get("user")
        if isinstance(user_raw, dict):
            user_data = user_raw
        elif "xdt_api__v1__discover__chaining" in payload_dict:
            chain_raw = payload_dict.get("xdt_api__v1__discover__chaining")
            if isinstance(chain_raw, dict):
                candidates = self._extract_candidate_dicts(chain_raw)
                if candidates:
                    user_data = candidates[0]

        if user_data and self._matches_target(user_data):
            if any(
                key in user_data
                for key in (
                    "is_private",
                    "follower_count",
                    "biography",
                    "full_name",
                )
            ):
                self.user_info = user_data

    def _collect_posts(self, payload_dict: dict[str, Any]) -> None:
        timeline_conn: Any | None = None
        if "xdt_api__v1__feed__user_timeline_graphql_connection" in payload_dict:
            timeline_conn = payload_dict.get(
                "xdt_api__v1__feed__user_timeline_graphql_connection"
            )
        if not timeline_conn and "user" in payload_dict:
            user_payload = safe_cast_to_dict(payload_dict.get("user"), {})
            timeline_conn = user_payload.get("edge_owner_to_timeline_media")

        timeline_dict = safe_cast_to_dict(timeline_conn, {})
        edges_or_items_raw = safe_cast_to_list(
            timeline_dict.get("edges") or timeline_dict.get("items"),
            [],
        )
        if not edges_or_items_raw and "user" in payload_dict:
            user_payload = safe_cast_to_dict(payload_dict.get("user"), {})
            legacy_timeline = safe_cast_to_dict(
                user_payload.get("edge_owner_to_timeline_media"),
                {},
            )
            edges_or_items_raw = safe_cast_to_list(
                legacy_timeline.get("edges") or legacy_timeline.get("items"),
                [],
            )
        edges: list[dict[str, Any]] = [
            cast(dict[str, Any], edge)
            for edge in edges_or_items_raw
            if isinstance(edge, dict)
        ]

        for edge in edges:
            if len(self.posts) >= self.max_posts:
                break
            node_data = safe_cast_to_dict(edge.get("node", edge), {})
            if not node_data:
                continue
            if not self._node_owner_matches(node_data):
                continue
            post = parse_post_info(node_data)
            if post.code and post.code in self._post_codes:
                continue
            if post.code:
                self._post_codes.add(post.code)
            self.posts.append(post)

    def _collect_reels(
        self,
        payload_dict: dict[str, Any],
        *,
        is_final: bool,
    ) -> None:
        clips_conn = safe_cast_to_dict(
            payload_dict.get("xdt_api__v1__clips__user__connection_v2"),
            {},
        )
        clips_edges_raw = safe_cast_to_list(
            clips_conn.get("edges") or clips_conn.get("items"),
            [],
        )
        clips_edges: list[dict[str, Any]] = [
            cast(dict[str, Any], edge)
            for edge in clips_edges_raw
            if isinstance(edge, dict)
        ]
        for edge in clips_edges:
            if len(self.reels) >= self.max_posts:
                break
            node = safe_cast_to_dict(edge.get("node"), {})
            media = safe_cast_to_dict(node.get("media"), {})
            if not media:
                continue
            if not self._node_owner_matches(media, fallback=node):
                continue
            reel = parse_reel_info(media)
            if reel.code and reel.code in self._reel_codes:
                continue
            if reel.code:
                self._reel_codes.add(reel.code)
            self.reels.append(reel)

        if (len(self.reels) >= min(3, self.max_posts)) or is_final:
            self.reels_done_event.set()

    def _collect_recommendations(self, payload_dict: dict[str, Any]) -> None:
        candidates, _has_recommendation_payload = (
            self._collect_recommendation_candidates(payload_dict)
        )
        if not candidates:
            return
        self._append_recommended_users(parse_suggested_users(candidates))

    def _collect_recommendation_candidates(
        self,
        payload_dict: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], bool]:
        candidates: list[dict[str, Any]] = []
        has_recommendation_payload = False

        for key, raw_value in payload_dict.items():
            if key == "user" or not isinstance(raw_value, dict):
                continue
            if "chaining" in key or "related" in key:
                has_recommendation_payload = True
                candidates.extend(self._extract_candidate_dicts(raw_value))

        user_payload = safe_cast_to_dict(payload_dict.get("user"), {})
        if user_payload:
            for key in ("edge_related_profiles", "related_profiles", "chaining"):
                raw_value = user_payload.get(key)
                if isinstance(raw_value, dict):
                    has_recommendation_payload = True
                    candidates.extend(self._extract_candidate_dicts(raw_value))
                elif isinstance(raw_value, list):
                    has_recommendation_payload = True
                    candidates.extend(
                        entry for entry in raw_value if isinstance(entry, dict)
                    )

            for key, raw_value in user_payload.items():
                if isinstance(raw_value, dict) and (
                    "chaining" in key or "related" in key
                ):
                    has_recommendation_payload = True
                    candidates.extend(self._extract_candidate_dicts(raw_value))

        if "xdt_api__v1__discover__chaining" in payload_dict:
            has_recommendation_payload = True

        return candidates, has_recommendation_payload

    @staticmethod
    def _extract_candidate_dicts(container: dict[str, Any]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []

        for list_key in ("users", "items", "related_profiles"):
            entries = container.get(list_key)
            if isinstance(entries, list):
                candidates.extend(entry for entry in entries if isinstance(entry, dict))

        edges = container.get("edges")
        if isinstance(edges, list):
            for edge in edges:
                if not isinstance(edge, dict):
                    continue
                node_candidate = edge.get("node") or edge.get("user")
                if isinstance(node_candidate, dict):
                    candidates.append(node_candidate)
                else:
                    candidates.append(edge)

        return candidates

    @staticmethod
    def _recommended_key(user: InstagramSuggestedUser) -> str | None:
        if user.id:
            return f"id:{user.id.strip()}"
        if user.username:
            return f"username:{user.username.strip().lower()}"
        return None

    def _append_recommended_users(
        self,
        users: list[InstagramSuggestedUser],
    ) -> None:
        for user in users:
            if (
                self.recommended_limit is not None
                and len(self.recommended_users) >= self.recommended_limit
            ):
                break

            key = self._recommended_key(user)
            if key and key in self._recommended_user_keys:
                continue
            if key:
                self._recommended_user_keys.add(key)
            self.recommended_users.append(user)

    def _node_owner_matches(
        self,
        node_data: dict[str, Any],
        *,
        fallback: dict[str, Any] | None = None,
    ) -> bool:
        if not self.target_username:
            return True
        owner_data = safe_cast_to_dict(
            node_data.get("owner") or node_data.get("user"),
            {},
        )
        if not owner_data and fallback is not None:
            owner_data = safe_cast_to_dict(
                fallback.get("owner") or fallback.get("user"),
                {},
            )
        if not owner_data:
            return True
        owner_username = owner_data.get("username")
        return not isinstance(owner_username, str) or (
            owner_username.strip().lower() == self.target_username
        )

    def _mark_ready_events(self) -> None:
        has_user_data = self.user_info is not None and any(
            key in self.user_info for key in ("is_private", "follower_count")
        )
        has_posts = len(self.posts) >= min(3, self.max_posts)
        if has_user_data and has_posts and not self.posts_ready_event.is_set():
            self.posts_ready_event.set()


def _is_graphql_json_response(response: Response) -> bool:
    request = response.request
    if not (
        request.method == "POST"
        and (
            "/graphql/query" in response.url
            or "/api/graphql" in response.url
            or "graphql.instagram.com" in response.url
        )
    ):
        return False
    if response.status != 200:
        return False
    content_type = response.headers.get("content-type", "").lower()
    return "json" in content_type or "javascript" in content_type


__all__ = ["InstagramScrapeCollector"]
