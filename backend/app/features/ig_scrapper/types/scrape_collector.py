from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, cast

from playwright.async_api import Page, Response

from ..classes import InstagramPost, InstagramReel, InstagramSuggestedUser
from .base import BaseInstagramWorker


class InstagramScrapeCollector:
    """Collect GraphQL data emitted during Instagram navigation flows."""

    def __init__(
        self,
        worker: BaseInstagramWorker,
        max_posts: int,
        target_username: str | None = None,
        recommended_limit: int | None = None,
        *,
        collect_posts: bool = True,
        collect_reels: bool = True,
        collect_recommendations: bool = True,
    ) -> None:
        self.worker = worker
        self.max_posts = max_posts
        self.collect_posts = collect_posts
        self.collect_reels = collect_reels
        self.collect_recommendations = collect_recommendations
        self.target_username = (
            target_username.strip().lower() if target_username else None
        )
        # TEMP: Hard cap for recommendation parsing to avoid extra CPU work.
        self.recommended_limit = recommended_limit

        self.posts_ready_event: asyncio.Event = asyncio.Event()
        self.reels_done_event: asyncio.Event = asyncio.Event()
        self.recommendations_ready_event: asyncio.Event = asyncio.Event()

        self.posts: list[InstagramPost] = []
        self.reels: list[InstagramReel] = []
        self.recommended_users: list[InstagramSuggestedUser] = []
        self._recommended_user_keys: set[str] = set()
        self.user_info: dict[str, Any] | None = None

    @property
    def logger(self) -> logging.Logger:
        return self.worker.logger

    def _matches_target(self, candidate: dict[str, Any]) -> bool:
        if not self.target_username:
            return True
        username = candidate.get("username")
        if isinstance(username, str) and username:
            return username.strip().lower() == self.target_username
        return False

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
            # TEMP: Stop parsing once recommendation cap is reached.
            if (
                self.recommended_limit is not None
                and len(self.recommended_users) >= self.recommended_limit
            ):
                self.recommendations_ready_event.set()
                break

            key = self._recommended_key(user)
            if key and key in self._recommended_user_keys:
                continue
            if key:
                self._recommended_user_keys.add(key)
            self.recommended_users.append(user)

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

        user_payload = self.worker.safe_cast_to_dict(payload_dict.get("user"), {})
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

    async def handle_response(self, resp: Response) -> None:
        try:
            # TEMP: Early drop for responses we no longer need to parse.
            needs_recommendations = self.collect_recommendations and not (
                self.recommendations_ready_event.is_set()
            )
            needs_posts = self.collect_posts and not self.posts_ready_event.is_set()
            needs_reels = self.collect_reels and not self.reels_done_event.is_set()
            if not (needs_recommendations or needs_posts or needs_reels):
                return

            if not (
                resp.request.method == "POST"
                and (
                    "/graphql/query" in resp.url
                    or "/api/graphql" in resp.url
                    or "graphql.instagram.com" in resp.url
                )
            ):
                return

            # TEMP: Skip non-200 and non-JSON responses before calling resp.json().
            if resp.status != 200:
                return

            content_type = resp.headers.get("content-type", "").lower()
            if "json" not in content_type:
                return

            data = await resp.json()
            if not isinstance(data, dict):
                return

            payload_dict = self.worker.safe_cast_to_dict(data.get("data"), {})
            extensions = self.worker.safe_cast_to_dict(data.get("extensions"), {})
            is_final = bool(extensions.get("is_final"))

            user_data: dict[str, Any] | None = None

            if "user" in payload_dict:
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

            if needs_recommendations:
                (
                    recommendation_candidates,
                    has_recommendation_payload,
                ) = self._collect_recommendation_candidates(payload_dict)
                if recommendation_candidates:
                    parsed_users = self.worker.parse_suggested_users(
                        recommendation_candidates
                    )
                    if parsed_users:
                        self._append_recommended_users(parsed_users)

                if self.recommended_users or (is_final and has_recommendation_payload):
                    self.recommendations_ready_event.set()

            if needs_posts:
                timeline_conn: Any | None = None
                if (
                    "xdt_api__v1__feed__user_timeline_graphql_connection"
                    in payload_dict
                ):
                    timeline_conn = payload_dict.get(
                        "xdt_api__v1__feed__user_timeline_graphql_connection"
                    )
                if not timeline_conn and "user" in payload_dict:
                    user_payload = self.worker.safe_cast_to_dict(
                        payload_dict.get("user"), {}
                    )
                    timeline_conn = user_payload.get("edge_owner_to_timeline_media")

                timeline_dict = self.worker.safe_cast_to_dict(timeline_conn, {})
                edges_or_items_raw = self.worker.safe_cast_to_list(
                    timeline_dict.get("edges") or timeline_dict.get("items"),
                    [],
                )

                if not edges_or_items_raw and "user" in payload_dict:
                    user_payload = self.worker.safe_cast_to_dict(
                        payload_dict.get("user"), {}
                    )
                    legacy_timeline = self.worker.safe_cast_to_dict(
                        user_payload.get("edge_owner_to_timeline_media"),
                        {},
                    )
                    edges_or_items_raw = self.worker.safe_cast_to_list(
                        legacy_timeline.get("edges") or legacy_timeline.get("items"),
                        [],
                    )

                edges: list[dict[str, Any]] = [
                    cast(dict[str, Any], edge)
                    for edge in edges_or_items_raw
                    if isinstance(edge, dict)
                ]

                for edge in edges:
                    node_candidate: Any = edge.get("node", edge)
                    node_data = self.worker.safe_cast_to_dict(node_candidate, {})
                    if len(self.posts) >= self.max_posts:
                        # TEMP: No need to iterate remaining edges when cap is reached.
                        break
                    if not node_data:
                        continue

                    owner_data = self.worker.safe_cast_to_dict(
                        node_data.get("owner") or node_data.get("user"),
                        {},
                    )
                    if self.target_username and owner_data:
                        owner_username = owner_data.get("username")
                        if (
                            isinstance(owner_username, str)
                            and owner_username.strip().lower() != self.target_username
                        ):
                            continue

                    if node_data:
                        self.posts.append(self.worker.parse_post_info(node_data))

            if (
                needs_reels
                and "xdt_api__v1__clips__user__connection_v2" in payload_dict
            ):
                clips_conn = self.worker.safe_cast_to_dict(
                    payload_dict.get("xdt_api__v1__clips__user__connection_v2"),
                    {},
                )
                clips_edges_raw = self.worker.safe_cast_to_list(
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
                        # TEMP: Stop reels parsing once cap is reached.
                        break
                    node = self.worker.safe_cast_to_dict(edge.get("node"), {})
                    media = self.worker.safe_cast_to_dict(node.get("media"), {})
                    owner_data = self.worker.safe_cast_to_dict(
                        media.get("owner") or node.get("user"),
                        {},
                    )
                    if self.target_username and owner_data:
                        owner_username = owner_data.get("username")
                        if (
                            isinstance(owner_username, str)
                            and owner_username.strip().lower() != self.target_username
                        ):
                            continue
                    if media and len(self.reels) < self.max_posts:
                        reel = InstagramReel()
                        code = media.get("code") or media.get("shortcode")
                        if isinstance(code, str):
                            reel.code = code
                        play_count = media.get("play_count")
                        if isinstance(play_count, int):
                            reel.play_count = play_count
                        comment_count = media.get("comment_count")
                        if isinstance(comment_count, int):
                            reel.comment_count = comment_count
                        like_count = media.get("like_count")
                        if isinstance(like_count, int):
                            reel.like_count = like_count
                        media_type = media.get("media_type")
                        if isinstance(media_type, int):
                            reel.media_type = media_type
                        product_type = media.get("product_type")
                        if isinstance(product_type, str):
                            reel.product_type = product_type
                        self.reels.append(reel)
                if (len(self.reels) >= min(3, self.max_posts)) or is_final:
                    self.reels_done_event.set()

            has_user_data = self.user_info is not None and any(
                key in self.user_info for key in ("is_private", "follower_count")
            )
            has_posts = len(self.posts) >= min(3, self.max_posts)

            if (
                self.collect_posts
                and has_user_data
                and has_posts
                and not self.posts_ready_event.is_set()
            ):
                self.posts_ready_event.set()

        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            self.logger.warning("Failed to parse GraphQL response: %s", exc)
        except Exception as exc:
            self.logger.error("Unexpected error processing response: %s", exc)

    def attach(self, page: Page) -> None:
        page.on("response", self.handle_response)

    def detach(self, page: Page) -> None:
        try:
            page.remove_listener("response", self.handle_response)
        except Exception as exc:
            self.logger.warning("Failed to remove response listener: %s", exc)


__all__ = ["InstagramScrapeCollector"]
