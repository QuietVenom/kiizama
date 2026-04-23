from app.features.social_media_report.service import TEMPLATES_DIR
from app.features.social_media_report.types.instagram_report_generator import (
    InstagramReportGenerator,
)


def _build_report_data(*, reels: list[dict[str, int | str]]) -> dict[str, object]:
    return {
        "scrape": {
            "user": {
                "username": "kimiish",
                "full_name": "Kimi Ish",
                "follower_count": 1200,
                "following_count": 120,
                "media_count": 24,
                "is_verified": False,
                "is_private": False,
                "profile_pic_url": None,
            },
            "posts": [
                {
                    "code": "POST1",
                    "like_count": 120,
                    "comment_count": 12,
                    "coauthor_producers": [],
                    "usertags": [],
                    "media_type": 1,
                }
            ],
            "reels": reels,
            "recommended_users": [],
            "ai_categories": [],
            "ai_roles": [],
        },
        "profile_url": "https://www.instagram.com/kimiish/",
    }


def test_social_media_report_hides_reels_section_when_no_reels() -> None:
    generator = InstagramReportGenerator(template_path=str(TEMPLATES_DIR))

    html = generator.generate_html(_build_report_data(reels=[]))

    assert "Reels (0 analizados)" not in html
    assert "Reels analizados" not in html
    assert "Reproducciones totales (reels)" not in html
    assert 'aria-label="Abrir reel' not in html


def test_social_media_report_renders_reels_section_when_reels_exist() -> None:
    generator = InstagramReportGenerator(template_path=str(TEMPLATES_DIR))

    html = generator.generate_html(
        _build_report_data(
            reels=[
                {
                    "code": "REEL1",
                    "play_count": 3400,
                    "like_count": 220,
                    "comment_count": 18,
                }
            ]
        )
    )

    assert "Reels (1 analizados)" in html
    assert "Reels analizados" in html
    assert "Reproducciones totales (reels)" in html
    assert 'aria-label="Abrir reel REEL1"' in html
