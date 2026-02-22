import logging
from collections.abc import Iterable, Mapping
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.features.general.types import HtmlPdfReportGenerator, enrich_profile_picture


def _get_field_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _coerce_dict(value: object) -> dict[str, Any]:
    if value is None:
        return {}

    if isinstance(value, type):
        return {}

    if isinstance(value, dict):
        return value

    if isinstance(value, Mapping):
        return dict(value)

    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)

    if isinstance(value, BaseModel):
        return value.model_dump()

    if isinstance(value, Mapping | Iterable):
        try:
            return dict(value)
        except (TypeError, ValueError):
            return {}

    return {}


def _coerce_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple | set):
        return list(value)
    return []


def calculate_metrics_from_scrape(scrape: Any) -> dict:
    """Calcula métricas de engagement a partir de datos de scraping."""
    scrape = scrape or {}
    user = _coerce_dict(_get_field_value(scrape, "user", {}))
    if not user:
        metrics = _get_field_value(scrape, "metrics", None)
        user = _coerce_dict(_get_field_value(metrics, "user", {}))

    posts = _coerce_list(_get_field_value(scrape, "posts", []))
    reels = _coerce_list(_get_field_value(scrape, "reels", []))
    recommended = _coerce_list(_get_field_value(scrape, "recommended_users", []))

    followers = user.get("follower_count", 0)
    followers = followers if isinstance(followers, int) else 0

    following = user.get("following_count", 0) if isinstance(user, dict) else 0
    following = following if isinstance(following, int) else 0

    media_count = user.get("media_count", 0) if isinstance(user, dict) else 0
    media_count = media_count if isinstance(media_count, int) else 0

    post_metrics = {
        "total_posts": len(posts),
        "total_likes": 0,
        "total_comments": 0,
        "avg_likes": 0.0,
        "avg_comments": 0.0,
        "avg_engagement_rate": 0.0,
        "hashtags_per_post": 0.0,
        "mentions_per_post": 0.0,
    }

    if posts:
        total_likes = 0
        total_comments = 0
        engagement_rates: list[float] = []
        total_hashtags = 0
        total_mentions = 0

        for post in posts:
            likes = _get_field_value(post, "like_count", 0) or 0
            comments = _get_field_value(post, "comment_count", 0) or 0
            if isinstance(likes, int):
                total_likes += likes
            if isinstance(comments, int):
                total_comments += comments
            engagement = (likes or 0) + (comments or 0)
            if followers:
                engagement_rates.append(engagement / followers)

            hashtags = _coerce_list(_get_field_value(post, "usertags", []))
            if hashtags:
                total_hashtags += len(hashtags)

            mentions = _coerce_list(_get_field_value(post, "coauthor_producers", []))
            if mentions:
                total_mentions += len(mentions)

        count_posts = len(posts)
        post_metrics["total_likes"] = total_likes
        post_metrics["total_comments"] = total_comments
        post_metrics["avg_likes"] = total_likes / count_posts if count_posts else 0.0
        post_metrics["avg_comments"] = (
            total_comments / count_posts if count_posts else 0.0
        )
        post_metrics["avg_engagement_rate"] = (
            sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0.0
        )
        post_metrics["hashtags_per_post"] = (
            total_hashtags / count_posts if count_posts else 0.0
        )
        post_metrics["mentions_per_post"] = (
            total_mentions / count_posts if count_posts else 0.0
        )

    reel_metrics = {
        "total_reels": len(reels),
        "total_plays": 0,
        "avg_plays": 0.0,
        "avg_reel_likes": 0.0,
        "avg_reel_comments": 0.0,
    }

    if reels:
        total_plays = 0
        total_likes = 0
        total_comments = 0

        for reel in reels:
            play_count = _get_field_value(reel, "play_count", 0)
            like_count = _get_field_value(reel, "like_count", 0)
            comment_count = _get_field_value(reel, "comment_count", 0)
            if isinstance(play_count, int):
                total_plays += play_count
            if isinstance(like_count, int):
                total_likes += like_count
            if isinstance(comment_count, int):
                total_comments += comment_count

        count_reels = len(reels)
        reel_metrics["total_plays"] = total_plays
        reel_metrics["avg_plays"] = total_plays / count_reels if count_reels else 0.0
        reel_metrics["avg_reel_likes"] = (
            total_likes / count_reels if count_reels else 0.0
        )
        reel_metrics["avg_reel_comments"] = (
            total_comments / count_reels if count_reels else 0.0
        )

    total_engagement = post_metrics["total_likes"] + post_metrics["total_comments"]
    overall_engagement_rate = total_engagement / followers if followers else 0.0

    return {
        "user": user,
        "post_metrics": post_metrics,
        "reel_metrics": reel_metrics,
        "overall_engagement_rate": overall_engagement_rate,
        "followers": followers,
        "following": following,
        "media_count": media_count,
        "is_verified": bool(user.get("is_verified"))
        if isinstance(user, dict)
        else False,
        "is_private": bool(user.get("is_private")) if isinstance(user, dict) else False,
        "recommended_users": recommended,
    }


class InstagramReportGenerator(HtmlPdfReportGenerator):
    """Genera reportes HTML y PDF a partir de datos de Instagram."""

    def __init__(
        self, template_path: str, template_name: str = "social_media_report.html"
    ):
        super().__init__(template_path=template_path, template_name=template_name)
        self.logger = logging.getLogger(__name__)

    def calculate_metrics(self, data: Any) -> dict:
        """Calcula métricas de engagement a partir de los datos."""
        scrape = self._get_field(data, "scrape", None)
        if scrape is None:
            if isinstance(data, dict) and any(
                key in data for key in ("user", "posts", "reels", "recommended_users")
            ):
                scrape = data
            elif any(
                hasattr(data, key)
                for key in ("user", "posts", "reels", "recommended_users")
            ):
                scrape = data
        return calculate_metrics_from_scrape(scrape)

    def build_context(self, data: Any) -> dict[str, Any]:
        metrics = self.calculate_metrics(data)
        profile = dict(metrics["user"])
        enrich_profile_picture(profile, logger=self.logger)

        scrape = self._get_field(data, "scrape", {})
        posts_raw = self._get_field(scrape, "posts", [])
        reels_raw = self._get_field(scrape, "reels", [])
        posts = self._normalize_posts(posts_raw)
        reels = self._normalize_reels(reels_raw)

        ai_categories = self._get_field(scrape, "ai_categories", [])
        ai_roles = self._get_field(scrape, "ai_roles", [])

        return {
            "report_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "profile": profile,
            "profile_url": self._get_field(data, "profile_url"),
            "metrics": metrics,
            "posts": posts,
            "reels": reels,
            "posts_limit": len(posts),
            "reels_limit": len(reels),
            "recommended_users": metrics["recommended_users"],
            "ai_categories": ai_categories,
            "ai_roles": ai_roles,
        }

    @staticmethod
    def _get_field(item: Any, key: str, default: Any = None) -> Any:
        """Retrieve attribute or dict key with a fallback."""
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)

    @classmethod
    def _normalize_posts(cls, posts: list[Any]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for post in posts or []:
            normalized.append(
                {
                    "code": cls._get_field(post, "code", ""),
                    "like_count": cls._safe_int(cls._get_field(post, "like_count")),
                    "comment_count": cls._safe_int(
                        cls._get_field(post, "comment_count")
                    ),
                    "coauthor_producers": cls._get_field(post, "coauthor_producers", [])
                    or [],
                    "usertags": cls._get_field(post, "usertags", []) or [],
                    "product_type": cls._get_field(post, "product_type", ""),
                }
            )
        return normalized

    @classmethod
    def _normalize_reels(cls, reels: list[Any]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for reel in reels or []:
            normalized.append(
                {
                    "code": cls._get_field(reel, "code", ""),
                    "play_count": cls._safe_int(cls._get_field(reel, "play_count")),
                    "like_count": cls._safe_int(cls._get_field(reel, "like_count")),
                    "comment_count": cls._safe_int(
                        cls._get_field(reel, "comment_count")
                    ),
                }
            )
        return normalized

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value) if value is not None else 0
        except (ValueError, TypeError):
            return 0


__all__ = ["InstagramReportGenerator", "calculate_metrics_from_scrape"]
