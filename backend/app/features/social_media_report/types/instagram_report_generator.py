import logging
from datetime import datetime
from typing import Any

from kiizama_scrape_core.ig_scraper.metrics import calculate_metrics_from_scrape

from app.features.general.types import HtmlPdfReportGenerator, enrich_profile_picture


class InstagramReportGenerator(HtmlPdfReportGenerator):
    """Genera reportes HTML y PDF a partir de datos de Instagram."""

    def __init__(
        self, template_path: str, template_name: str = "social_media_report.html"
    ):
        super().__init__(template_path=template_path, template_name=template_name)
        self.logger = logging.getLogger(__name__)

    def calculate_metrics(self, data: Any) -> dict[str, Any]:
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
                    "media_type": cls._get_field(post, "media_type"),
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
