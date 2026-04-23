import uuid
from datetime import UTC, datetime


def post_payload(
    *, profile_id: str | None = None, code: str = "POST1"
) -> dict[str, object]:
    return {
        "profile_id": profile_id or str(uuid.uuid4()),
        "updated_at": datetime.now(UTC).isoformat(),
        "posts": [{"code": code, "caption_text": "caption", "like_count": 10}],
    }


def reel_payload(
    *, profile_id: str | None = None, code: str = "REEL1"
) -> dict[str, object]:
    return {
        "profile_id": profile_id or str(uuid.uuid4()),
        "updated_at": datetime.now(UTC).isoformat(),
        "reels": [{"code": code, "play_count": 100, "like_count": 10}],
    }


def metrics_payload() -> dict[str, object]:
    return {
        "post_metrics": {
            "total_posts": 2,
            "total_likes": 30,
            "total_comments": 3,
            "avg_likes": 15.0,
            "avg_comments": 1.5,
            "avg_engagement_rate": 0.5,
            "hashtags_per_post": 1.0,
            "mentions_per_post": 0.0,
        },
        "reel_metrics": {
            "total_reels": 1,
            "total_plays": 100,
            "avg_plays": 100.0,
            "avg_reel_likes": 10.0,
            "avg_reel_comments": 1.0,
        },
        "overall_post_engagement_rate": 0.5,
        "reel_engagement_rate_on_plays": 0.11,
    }
