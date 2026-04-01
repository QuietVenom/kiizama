from app.features.brand_intelligence.services.service_config import TEMPLATES_DIR
from app.features.brand_intelligence.types import (
    ReputationCampaignStrategyReportGenerator,
    ReputationCreatorStrategyReportGenerator,
)


def test_campaign_strategy_hides_reel_metrics_when_no_reels() -> None:
    generator = ReputationCampaignStrategyReportGenerator(
        template_path=str(TEMPLATES_DIR)
    )

    html = generator.generate_html(
        {
            "brand_name": "Kiizama",
            "brand_urls": [],
            "report_main_body": "<section><h2>Strategy</h2><p>Body</p></section>",
            "influencer_profiles_directory": [
                {
                    "username": "kimiish",
                    "full_name": "Kimi Ish",
                    "biography": "Bio",
                    "profile_pic_url": "",
                    "follower_count": 1200,
                    "is_verified": False,
                    "ai_categories": [],
                    "ai_roles": [],
                    "metrics": {
                        "total_posts": 4,
                        "total_comments": 12,
                        "total_likes": 220,
                        "avg_engagement_rate": 0.12,
                        "hashtags_per_post": 1.5,
                        "mentions_per_post": 0.75,
                        "total_reels": 0,
                        "total_plays": 0,
                        "overall_post_engagement_rate": 0.13,
                        "reel_engagement_rate_on_plays": 0.0,
                    },
                }
            ],
        }
    )

    assert "Total reels" not in html
    assert "Total plays" not in html
    assert "Reel engagement rate on plays" not in html


def test_campaign_strategy_renders_reel_metrics_when_reels_exist() -> None:
    generator = ReputationCampaignStrategyReportGenerator(
        template_path=str(TEMPLATES_DIR)
    )

    html = generator.generate_html(
        {
            "brand_name": "Kiizama",
            "brand_urls": [],
            "report_main_body": "<section><h2>Strategy</h2><p>Body</p></section>",
            "influencer_profiles_directory": [
                {
                    "username": "kimiish",
                    "full_name": "Kimi Ish",
                    "biography": "Bio",
                    "profile_pic_url": "",
                    "follower_count": 1200,
                    "is_verified": False,
                    "ai_categories": [],
                    "ai_roles": [],
                    "metrics": {
                        "total_posts": 4,
                        "total_comments": 12,
                        "total_likes": 220,
                        "avg_engagement_rate": 0.12,
                        "hashtags_per_post": 1.5,
                        "mentions_per_post": 0.75,
                        "total_reels": 2,
                        "total_plays": 5000,
                        "overall_post_engagement_rate": 0.13,
                        "reel_engagement_rate_on_plays": 0.0475,
                    },
                }
            ],
        }
    )

    assert "Total reels" in html
    assert "Total plays" in html
    assert "Reel engagement rate on plays" in html


def test_creator_strategy_hides_reel_metrics_when_no_reels() -> None:
    generator = ReputationCreatorStrategyReportGenerator(
        template_path=str(TEMPLATES_DIR)
    )

    html = generator.generate_html(
        {
            "creator_username": "kimiish",
            "creator_full_name": "Kimi Ish",
            "report_main_body": "<section><h2>Strategy</h2><p>Body</p></section>",
            "current_metrics": {
                "creator_full_name": "Kimi Ish",
                "creator_follower_count": 1200,
                "total_likes": 220,
                "avg_engagement_rate": 0.12,
                "hashtags_per_post": 1.5,
                "mentions_per_post": 0.75,
                "total_reels": 0,
                "total_plays": 0,
                "overall_post_engagement_rate": 0.13,
                "reel_engagement_rate_on_plays": 0.0,
                "reels_metrics_status": "unavailable",
            },
        }
    )

    assert "<td>total_reels</td>" not in html
    assert "<td>total_plays</td>" not in html
    assert "<td>reel_engagement_rate_on_plays</td>" not in html
    assert "reels_metrics_status" not in html


def test_creator_strategy_renders_reel_metrics_when_reels_exist() -> None:
    generator = ReputationCreatorStrategyReportGenerator(
        template_path=str(TEMPLATES_DIR)
    )

    html = generator.generate_html(
        {
            "creator_username": "kimiish",
            "creator_full_name": "Kimi Ish",
            "report_main_body": "<section><h2>Strategy</h2><p>Body</p></section>",
            "current_metrics": {
                "creator_full_name": "Kimi Ish",
                "creator_follower_count": 1200,
                "total_likes": 220,
                "avg_engagement_rate": 0.12,
                "hashtags_per_post": 1.5,
                "mentions_per_post": 0.75,
                "total_reels": 2,
                "total_plays": 5000,
                "overall_post_engagement_rate": 0.13,
                "reel_engagement_rate_on_plays": 0.0475,
                "reels_metrics_status": "available",
            },
        }
    )

    assert "<td>total_reels</td>" in html
    assert "<td>total_plays</td>" in html
    assert "<td>reel_engagement_rate_on_plays</td>" in html
    assert "reels_metrics_status" not in html
