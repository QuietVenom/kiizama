import asyncio

from app.features.brand_intelligence.schemas import (
    InfluencerMetricsSummary,
    InfluencerProfileDirectoryItem,
)
from app.features.brand_intelligence.service import check_profile_usernames_existence
from app.features.brand_intelligence.services.service_costs import build_cost_analysis
from app.features.brand_intelligence.services.service_utils import (
    build_campaign_template_name,
    build_creator_template_name,
    coerce_mapping,
    normalize_string_list,
    safe_float,
    safe_int,
    snapshot_is_more_recent,
    string_or_none,
)


class FakeBrandRepository:
    async def fetch_profiles_by_usernames(self, profiles_collection, usernames):
        del profiles_collection, usernames
        return [
            {
                "username": "creator_one",
                "updated_date": "2026-04-01T00:00:00Z",
            }
        ]


def test_check_profile_usernames_existence_normalizes_duplicates_and_marks_missing() -> (
    None
):
    result = asyncio.run(
        check_profile_usernames_existence(
            [" Creator_One ", "missing", "creator_one"],
            profiles_collection=object(),
            repository=FakeBrandRepository(),
        )
    )

    assert [item.username for item in result.profiles] == [
        "creator_one",
        "missing",
        "creator_one",
    ]
    assert [item.exists for item in result.profiles] == [True, False, True]


def test_build_cost_analysis_classifies_known_and_unclassified_profiles() -> None:
    analysis = build_cost_analysis(
        [
            InfluencerProfileDirectoryItem(
                username="nano",
                follower_count=1_500,
                metrics=InfluencerMetricsSummary(),
            ),
            InfluencerProfileDirectoryItem(
                username="unclassified",
                follower_count=0,
                metrics=InfluencerMetricsSummary(),
            ),
        ]
    )

    assert analysis.summary.total_profiles == 2
    assert analysis.summary.classified_profiles == 1
    assert analysis.summary.unclassified_profiles == 1
    assert analysis.summary.total_average_mxn > 0
    assert analysis.summary_by_segment[-1].tier_key == "unclassified"


def test_service_utils_coerce_values_and_build_safe_template_names() -> None:
    assert coerce_mapping({"a": 1}) == {"a": 1}
    assert normalize_string_list(["a", None, 2]) == ["a", "2"]
    assert string_or_none("  ") is None
    assert safe_int("12") == 12
    assert safe_int("bad") == 0
    assert safe_float("1.5") == 1.5
    assert build_campaign_template_name("ACME Beauty!") == (
        "reputation_campaign_strategy_acme_beauty.html"
    )
    assert build_creator_template_name(" Creator One! ") == (
        "reputation_creator_strategy_creator_one.html"
    )


def test_snapshot_is_more_recent_handles_missing_values() -> None:
    assert snapshot_is_more_recent({"scraped_at": 2}, {"scraped_at": 1}) is True
    assert snapshot_is_more_recent({"scraped_at": None}, {"scraped_at": 1}) is False
    assert snapshot_is_more_recent({"scraped_at": 2}, {"scraped_at": None}) is True
