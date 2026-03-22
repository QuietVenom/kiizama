from __future__ import annotations

from typing import Any

from kiizama_scrape_core.ig_scraper.utils import should_refresh_profile

from app.features.openai.classes import (
    render_creator_strategy_sections_html,
    render_reputation_strategy_sections_html,
)

from .classes import CAMPAIGN_TYPE_OPTIONS_BY_NAME
from .repository import BrandIntelligenceRepository
from .schemas import (
    CampaignTypeCatalogItem,
    ProfileExistenceCollection,
    ProfileExistenceItem,
    ReputationCampaignStrategyConfirmResponse,
    ReputationCampaignStrategyRequest,
    ReputationCreatorStrategyConfirmResponse,
    ReputationCreatorStrategyRequest,
    build_campaign_type_catalog,
    normalize_lookup_usernames,
)
from .services.service_config import CAMPAIGN_TEMPLATE_PATH, CREATOR_TEMPLATE_PATH
from .services.service_costs import build_cost_analysis, build_cost_tier_directory
from .services.service_profiles import (
    build_creator_profile_summary,
    build_influencer_profiles_directory,
)
from .services.service_reporting import ReportFile, generate_report_files
from .services.service_strategy import (
    build_report_context,
    generate_reputation_creator_strategy_output,
    generate_reputation_strategy_output,
)
from .services.service_utils import (
    build_campaign_template_name,
    build_creator_template_name,
)
from .types import (
    ReputationCampaignStrategyReportGenerator,
    ReputationCreatorStrategyReportGenerator,
)


async def generate_reputation_campaign_strategy_report(
    profiles_collection: Any,
    profile_snapshots_collection: Any,
    payload: ReputationCampaignStrategyRequest | dict[str, Any],
    repository: BrandIntelligenceRepository | None = None,
) -> list[ReportFile]:
    request = (
        payload
        if isinstance(payload, ReputationCampaignStrategyRequest)
        else ReputationCampaignStrategyRequest(**payload)
    )

    confirmation = await confirm_reputation_campaign_strategy(
        request,
        profiles_collection=profiles_collection,
        profile_snapshots_collection=profile_snapshots_collection,
        repository=repository,
    )
    context = build_report_context(confirmation)
    strategy_output = await generate_reputation_strategy_output(context)
    context["reputation_strategy"] = strategy_output.to_dict()
    context["report_main_body"] = render_reputation_strategy_sections_html(
        strategy_output
    )

    generator = ReputationCampaignStrategyReportGenerator(
        template_path=str(CAMPAIGN_TEMPLATE_PATH.parent),
        template_name=CAMPAIGN_TEMPLATE_PATH.name,
    )

    return await generate_report_files(
        confirmation_template_name=confirmation.template_name,
        context=context,
        generate_html=request.generate_html,
        generate_pdf=request.generate_pdf,
        generator=generator,
    )


async def generate_reputation_creator_strategy_report(
    profiles_collection: Any,
    profile_snapshots_collection: Any,
    payload: ReputationCreatorStrategyRequest | dict[str, Any],
    repository: BrandIntelligenceRepository | None = None,
) -> list[ReportFile]:
    request = (
        payload
        if isinstance(payload, ReputationCreatorStrategyRequest)
        else ReputationCreatorStrategyRequest(**payload)
    )

    confirmation = await confirm_reputation_creator_strategy(
        request,
        profiles_collection=profiles_collection,
        profile_snapshots_collection=profile_snapshots_collection,
        repository=repository,
    )
    context = build_report_context(
        confirmation,
        ensure_current_metrics=True,
    )
    strategy_output = await generate_reputation_creator_strategy_output(context)
    context["reputation_strategy"] = strategy_output.to_dict()
    context["report_main_body"] = render_creator_strategy_sections_html(strategy_output)

    generator = ReputationCreatorStrategyReportGenerator(
        template_path=str(CREATOR_TEMPLATE_PATH.parent),
        template_name=CREATOR_TEMPLATE_PATH.name,
    )

    return await generate_report_files(
        confirmation_template_name=confirmation.template_name,
        context=context,
        generate_html=request.generate_html,
        generate_pdf=request.generate_pdf,
        generator=generator,
    )


async def confirm_reputation_campaign_strategy(
    payload: ReputationCampaignStrategyRequest | dict[str, Any],
    profiles_collection: Any,
    profile_snapshots_collection: Any,
    repository: BrandIntelligenceRepository | None = None,
) -> ReputationCampaignStrategyConfirmResponse:
    request = (
        payload
        if isinstance(payload, ReputationCampaignStrategyRequest)
        else ReputationCampaignStrategyRequest(**payload)
    )
    repo = repository or BrandIntelligenceRepository()

    selected_campaign_option = CAMPAIGN_TYPE_OPTIONS_BY_NAME[request.campaign_type]
    selected_campaign_types = [
        CampaignTypeCatalogItem(
            name=selected_campaign_option.name,
            title=selected_campaign_option.title,
            value=selected_campaign_option.value,
        )
    ]

    profiles = await repo.fetch_profiles_by_usernames(
        profiles_collection,
        request.profiles_list,
    )
    snapshots = await repo.fetch_snapshots_full_by_usernames(
        profile_snapshots_collection,
        request.profiles_list,
    )
    (
        influencer_profiles_directory,
        missing_profiles,
    ) = build_influencer_profiles_directory(
        request.profiles_list,
        profiles=profiles,
        snapshots=snapshots,
    )
    cost_tier_directory = build_cost_tier_directory()
    cost_analysis = build_cost_analysis(influencer_profiles_directory)

    return ReputationCampaignStrategyConfirmResponse(
        message=(
            "Payload recibido y validado correctamente. "
            "Se construyeron los directorios de perfiles y costos estimados."
        ),
        payload=request,
        template_name=build_campaign_template_name(request.brand_name),
        template_path=str(CAMPAIGN_TEMPLATE_PATH),
        campaign_type_catalog=build_campaign_type_catalog(),
        cost_tier_directory=cost_tier_directory,
        selected_campaign_types=selected_campaign_types,
        influencer_profiles_directory=influencer_profiles_directory,
        cost_analysis=cost_analysis,
        missing_profiles=missing_profiles,
    )


async def check_profile_usernames_existence(
    usernames: list[str] | None,
    profiles_collection: Any,
    repository: BrandIntelligenceRepository | None = None,
) -> ProfileExistenceCollection:
    normalized_usernames = normalize_lookup_usernames(usernames)
    repo = repository or BrandIntelligenceRepository()

    unique_usernames = list(dict.fromkeys(normalized_usernames))
    profiles = await repo.fetch_profiles_by_usernames(
        profiles_collection,
        unique_usernames,
    )
    profiles_by_username = {
        str(profile.get("username")).lower(): profile
        for profile in profiles
        if isinstance(profile.get("username"), str)
    }

    return ProfileExistenceCollection(
        profiles=[
            ProfileExistenceItem(
                username=username,
                exists=username in profiles_by_username,
                expired=should_refresh_profile(profiles_by_username.get(username)),
            )
            for username in normalized_usernames
        ]
    )


async def confirm_reputation_creator_strategy(
    payload: ReputationCreatorStrategyRequest | dict[str, Any],
    profiles_collection: Any,
    profile_snapshots_collection: Any,
    repository: BrandIntelligenceRepository | None = None,
) -> ReputationCreatorStrategyConfirmResponse:
    request = (
        payload
        if isinstance(payload, ReputationCreatorStrategyRequest)
        else ReputationCreatorStrategyRequest(**payload)
    )
    repo = repository or BrandIntelligenceRepository()

    profiles = await repo.fetch_profiles_by_usernames(
        profiles_collection,
        [request.creator_username],
    )
    snapshots = await repo.fetch_snapshots_full_by_usernames(
        profile_snapshots_collection,
        [request.creator_username],
    )

    creator_summary = build_creator_profile_summary(
        request.creator_username,
        profiles=profiles,
        snapshots=snapshots,
    )
    resolved_current_metrics = creator_summary["current_metrics"]

    return ReputationCreatorStrategyConfirmResponse(
        message=(
            "Payload recibido y validado correctamente. "
            "Se construyo el perfil consolidado del creador."
        ),
        payload=request,
        template_name=build_creator_template_name(request.creator_username),
        template_path=str(CREATOR_TEMPLATE_PATH),
        creator_full_name=creator_summary["full_name"],
        creator_biography=creator_summary["biography"],
        creator_profile_pic_url=creator_summary["profile_pic_url"],
        creator_is_verified=creator_summary["is_verified"],
        creator_follower_count=creator_summary["follower_count"],
        creator_ai_categories=creator_summary["ai_categories"],
        creator_ai_roles=creator_summary["ai_roles"],
        current_metrics=resolved_current_metrics,
        missing_creator=creator_summary["missing_creator"],
    )


__all__ = [
    "check_profile_usernames_existence",
    "confirm_reputation_campaign_strategy",
    "confirm_reputation_creator_strategy",
    "generate_reputation_campaign_strategy_report",
    "generate_reputation_creator_strategy_report",
    "ReportFile",
]
