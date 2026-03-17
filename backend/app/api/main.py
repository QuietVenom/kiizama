from fastapi import APIRouter

from app.api.routes import (
    brand_intelligence,
    events,
    feature_flags,
    health,
    ig_credentials,
    ig_metrics,
    ig_posts,
    ig_profile,
    ig_profile_snapshots,
    ig_reels,
    ig_scrapper,
    internal_login,
    login,
    openai,
    private,
    social_media_report,
    users,
    utils,
)
from app.api.routes.public import feature_flags as public_feature_flags
from app.api.routes.public import waiting_list as public_waiting_list
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(login.router)
api_router.include_router(internal_login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(feature_flags.router)
api_router.include_router(public_feature_flags.router)
api_router.include_router(public_waiting_list.router)
api_router.include_router(events.router)
api_router.include_router(ig_credentials.router)
api_router.include_router(ig_profile.router)
api_router.include_router(ig_posts.router)
api_router.include_router(ig_reels.router)
api_router.include_router(ig_metrics.router)
api_router.include_router(ig_profile_snapshots.router)
api_router.include_router(ig_scrapper.router)
api_router.include_router(social_media_report.router)
api_router.include_router(openai.router)
api_router.include_router(brand_intelligence.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
