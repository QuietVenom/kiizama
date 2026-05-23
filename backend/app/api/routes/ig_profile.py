import logging
from math import ceil
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from kiizama_scrape_core.ig_scraper_v2.utils import should_refresh_profile
from pydantic import BaseModel, ValidationError

from app.api.deps import (
    CurrentUser,
    get_current_active_superuser,
    get_profiles_collection,
)
from app.crud.profile import (
    create_profile,
    delete_profile,
    get_profile,
    get_profile_by_username,
    get_profiles_by_usernames,
    list_profiles,
    replace_profile,
    search_profiles,
    update_profile,
)
from app.crud.profile_snapshots import get_profile_snapshot_full_by_profile_id
from app.features.general.types import (
    is_allowed_profile_picture_url,
    resolve_profile_picture_data_uri,
)
from app.features.rate_limit import POLICIES, rate_limit
from app.models import User
from app.schemas import (
    Profile,
    ProfileCollection,
    ProfileSearchFilters,
    ProfileSearchPagination,
    ProfileSearchResponse,
    ProfileSearchSortBy,
    ProfileSearchSortOrder,
    ProfileSnapshotFull,
    UpdateProfile,
)

router = APIRouter(prefix="/ig-profiles", tags=["ig-profiles"])

Document = dict[str, Any]
logger = logging.getLogger(__name__)


class ProfileUsernames(BaseModel):
    usernames: list[str]


def _build_profile_search_filters(
    query: Annotated[str | None, Query(min_length=3, max_length=100)] = None,
    ai_categories: Annotated[list[str] | None, Query(max_length=25)] = None,
    ai_roles: Annotated[list[str] | None, Query(max_length=25)] = None,
    follower_count_min: Annotated[int | None, Query(ge=0)] = None,
    follower_count_max: Annotated[int | None, Query(ge=0)] = None,
    sort_by: Annotated[ProfileSearchSortBy, Query()] = "follower_count",
    sort_order: Annotated[ProfileSearchSortOrder, Query()] = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProfileSearchFilters:
    try:
        return ProfileSearchFilters(
            query=query,
            ai_categories=ai_categories or [],
            ai_roles=ai_roles or [],
            follower_count_min=follower_count_min,
            follower_count_max=follower_count_max,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


def _build_profile_search_pagination(
    *,
    filters: ProfileSearchFilters,
    total: int,
) -> ProfileSearchPagination:
    total_pages = ceil(total / filters.page_size) if total else 0
    return ProfileSearchPagination(
        page=filters.page,
        page_size=filters.page_size,
        total=total,
        total_pages=total_pages,
        has_next=filters.page < total_pages,
        has_previous=filters.page > 1,
    )


def _require_profile(profile_doc: Document | None) -> Profile:
    if not profile_doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    return Profile.model_validate(profile_doc)


def _require_profile_snapshot_full(
    snapshot_doc: Document | None,
) -> ProfileSnapshotFull:
    if not snapshot_doc:
        raise HTTPException(status_code=404, detail="Profile snapshot not found")
    return ProfileSnapshotFull.model_validate(snapshot_doc)


def _enrich_profile_snapshot_picture_source(snapshot_doc: Document) -> None:
    profile = snapshot_doc.get("profile")
    if not isinstance(profile, dict):
        return

    profile_pic_url = profile.get("profile_pic_url")
    if (
        not isinstance(profile_pic_url, str)
        or not profile_pic_url
        or not is_allowed_profile_picture_url(profile_pic_url)
    ):
        return

    resolved_source = resolve_profile_picture_data_uri(profile_pic_url, logger)
    if isinstance(resolved_source, str) and resolved_source:
        profile["profile_pic_src"] = resolved_source


@router.post("/", response_model=Profile, status_code=status.HTTP_201_CREATED)
def create_ig_profile(
    profile: Profile,
    collection: Any = Depends(get_profiles_collection),
    _current_user: User = Depends(get_current_active_superuser),
) -> Profile:
    created = create_profile(collection, profile)
    return _require_profile(created)


@router.get(
    "/by-username/{username}",
    response_model=Profile,
    dependencies=[Depends(rate_limit(POLICIES.private_basic))],
)
def read_ig_profile_by_username(
    username: str,
    _current_user: CurrentUser,
    collection: Any = Depends(get_profiles_collection),
) -> Profile:
    return _require_profile(get_profile_by_username(collection, username))


@router.post("/by-usernames", response_model=ProfileCollection)
def read_ig_profiles_by_usernames(
    payload: ProfileUsernames,
    collection: Any = Depends(get_profiles_collection),
    _current_user: User = Depends(get_current_active_superuser),
) -> ProfileCollection:
    if not payload.usernames:
        raise HTTPException(status_code=400, detail="usernames cannot be empty")
    profiles = get_profiles_by_usernames(collection, payload.usernames)
    return ProfileCollection(
        profiles=[Profile.model_validate(profile) for profile in profiles]
    )


@router.get(
    "/search",
    response_model=ProfileSearchResponse,
    dependencies=[Depends(rate_limit(POLICIES.private_basic))],
)
def search_ig_profiles(
    filters: Annotated[ProfileSearchFilters, Depends(_build_profile_search_filters)],
    _current_user: CurrentUser,
    collection: Any = Depends(get_profiles_collection),
) -> ProfileSearchResponse:
    profiles, total = search_profiles(collection, filters)
    return ProfileSearchResponse(
        profiles=[Profile.model_validate(profile) for profile in profiles],
        pagination=_build_profile_search_pagination(filters=filters, total=total),
    )


@router.get("/", response_model=ProfileCollection)
def read_ig_profiles(
    skip: int = 0,
    limit: int = 100,
    collection: Any = Depends(get_profiles_collection),
    _current_user: User = Depends(get_current_active_superuser),
) -> ProfileCollection:
    profiles = list_profiles(collection, skip=skip, limit=limit)
    return ProfileCollection(
        profiles=[Profile.model_validate(profile) for profile in profiles]
    )


@router.get(
    "/{profile_id}/full-profile",
    response_model=ProfileSnapshotFull,
    dependencies=[Depends(rate_limit(POLICIES.private_expensive))],
)
def read_ig_profile_full_profile(
    profile_id: str,
    _current_user: CurrentUser,
    collection: Any = Depends(get_profiles_collection),
) -> ProfileSnapshotFull:
    _require_profile(get_profile(collection, profile_id))
    snapshot = get_profile_snapshot_full_by_profile_id(collection, profile_id)
    if snapshot and isinstance(snapshot.get("profile"), dict):
        _enrich_profile_snapshot_picture_source(snapshot)
        snapshot["update_required"] = should_refresh_profile(snapshot["profile"])
    return _require_profile_snapshot_full(snapshot)


@router.get("/{profile_id}", response_model=Profile)
def read_ig_profile(
    profile_id: str,
    collection: Any = Depends(get_profiles_collection),
    _current_user: User = Depends(get_current_active_superuser),
) -> Profile:
    return _require_profile(get_profile(collection, profile_id))


@router.patch("/{profile_id}", response_model=Profile)
def update_ig_profile(
    profile_id: str,
    patch: UpdateProfile,
    collection: Any = Depends(get_profiles_collection),
    _current_user: User = Depends(get_current_active_superuser),
) -> Profile:
    return _require_profile(update_profile(collection, profile_id, patch))


@router.put("/{profile_id}", response_model=Profile)
def replace_ig_profile(
    profile_id: str,
    profile_in: Profile,
    collection: Any = Depends(get_profiles_collection),
    _current_user: User = Depends(get_current_active_superuser),
) -> Profile:
    return _require_profile(replace_profile(collection, profile_id, profile_in))


@router.delete("/{profile_id}", response_model=Profile)
def delete_ig_profile(
    profile_id: str,
    collection: Any = Depends(get_profiles_collection),
    _current_user: User = Depends(get_current_active_superuser),
) -> Profile:
    return _require_profile(delete_profile(collection, profile_id))


__all__ = ["router"]
