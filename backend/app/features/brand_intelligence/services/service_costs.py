from __future__ import annotations

from collections.abc import Sequence

from ..classes import INFLUENCER_COST_TIER_OPTIONS, CostTierOption
from ..schemas import (
    CostAnalysis,
    CostAnalysisSummary,
    CostSegmentSummaryItem,
    CostTierCatalogItem,
    InfluencerProfileDirectoryItem,
)


def build_cost_tier_directory() -> list[CostTierCatalogItem]:
    return [
        CostTierCatalogItem(
            key=tier.key,
            label=tier.label,
            min_followers=tier.min_followers,
            max_followers=tier.max_followers,
            typical_deliverable=tier.typical_deliverable,
            min_mxn=tier.min_mxn,
            max_mxn=tier.max_mxn,
            average_mxn=tier.average_mxn,
            notes=tier.notes,
            is_manual=tier.is_manual,
        )
        for tier in INFLUENCER_COST_TIER_OPTIONS
    ]


def build_cost_analysis(
    influencer_profiles_directory: Sequence[InfluencerProfileDirectoryItem],
) -> CostAnalysis:
    segments_map: dict[str, CostSegmentSummaryItem] = {}
    total_min_mxn = 0
    total_max_mxn = 0
    total_average_mxn = 0
    classified_profiles = 0

    for influencer in influencer_profiles_directory:
        tier = resolve_cost_tier_by_followers(influencer.follower_count)
        if tier is not None:
            classified_profiles += 1
            total_min_mxn += tier.min_mxn
            total_max_mxn += tier.max_mxn
            total_average_mxn += tier.average_mxn
            segment = segments_map.get(tier.key)
            if segment is None:
                segment = CostSegmentSummaryItem(
                    tier_key=tier.key,
                    tier_label=tier.label,
                    profiles_count=0,
                    typical_deliverable=tier.typical_deliverable,
                    segment_min_mxn=0,
                    segment_max_mxn=0,
                    segment_average_mxn=0,
                    notes=tier.notes,
                )
                segments_map[tier.key] = segment
            segment.profiles_count += 1
            segment.segment_min_mxn += tier.min_mxn
            segment.segment_max_mxn += tier.max_mxn
            segment.segment_average_mxn += tier.average_mxn
            continue

        unclassified_key = "unclassified"
        unclassified = segments_map.get(unclassified_key)
        if unclassified is None:
            unclassified = CostSegmentSummaryItem(
                tier_key=unclassified_key,
                tier_label="Unclassified",
                profiles_count=0,
                typical_deliverable=None,
                segment_min_mxn=0,
                segment_max_mxn=0,
                segment_average_mxn=0,
                notes="Follower count does not match a standard pricing tier.",
            )
            segments_map[unclassified_key] = unclassified
        unclassified.profiles_count += 1

    total_profiles = len(influencer_profiles_directory)
    summary = CostAnalysisSummary(
        currency="MXN",
        total_profiles=total_profiles,
        classified_profiles=classified_profiles,
        unclassified_profiles=max(total_profiles - classified_profiles, 0),
        total_min_mxn=total_min_mxn,
        total_max_mxn=total_max_mxn,
        total_average_mxn=total_average_mxn,
    )

    summary_by_segment = order_segment_summary(segments_map)
    return CostAnalysis(
        summary=summary,
        summary_by_segment=summary_by_segment,
    )


def order_segment_summary(
    segments_map: dict[str, CostSegmentSummaryItem],
) -> list[CostSegmentSummaryItem]:
    ordered: list[CostSegmentSummaryItem] = []
    for tier in INFLUENCER_COST_TIER_OPTIONS:
        segment = segments_map.get(tier.key)
        if segment is not None and segment.profiles_count > 0:
            ordered.append(segment)

    unclassified = segments_map.get("unclassified")
    if unclassified is not None and unclassified.profiles_count > 0:
        ordered.append(unclassified)
    return ordered


def resolve_cost_tier_by_followers(follower_count: int) -> CostTierOption | None:
    for tier in INFLUENCER_COST_TIER_OPTIONS:
        if tier.is_manual:
            continue
        if matches_follower_range(
            follower_count,
            min_followers=tier.min_followers,
            max_followers=tier.max_followers,
        ):
            return tier
    return None


def matches_follower_range(
    value: int,
    *,
    min_followers: int | None,
    max_followers: int | None,
) -> bool:
    if min_followers is not None and value < min_followers:
        return False
    if max_followers is not None and value > max_followers:
        return False
    return True


__all__ = [
    "build_cost_tier_directory",
    "build_cost_analysis",
]
