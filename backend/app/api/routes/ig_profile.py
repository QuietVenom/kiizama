from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

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
    update_profile,
)
from app.features.rate_limit import POLICIES, rate_limit
from app.models import User
from app.schemas import Profile, ProfileCollection, UpdateProfile

router = APIRouter(prefix="/ig-profiles", tags=["ig-profiles"])

Document = dict[str, Any]


class ProfileUsernames(BaseModel):
    usernames: list[str]


def _require_profile(profile_doc: Document | None) -> Profile:
    if not profile_doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    return Profile.model_validate(profile_doc)


@router.post("/", response_model=Profile, status_code=status.HTTP_201_CREATED)
async def create_ig_profile(
    profile: Profile,
    collection: Any = Depends(get_profiles_collection),
    _current_user: User = Depends(get_current_active_superuser),
) -> Profile:
    created = await create_profile(collection, profile)
    return _require_profile(created)


@router.get(
    "/by-username/{username}",
    response_model=Profile,
    dependencies=[Depends(rate_limit(POLICIES.private_basic))],
)
async def read_ig_profile_by_username(
    username: str,
    _current_user: CurrentUser,
    collection: Any = Depends(get_profiles_collection),
) -> Profile:
    return _require_profile(await get_profile_by_username(collection, username))


@router.post("/by-usernames", response_model=ProfileCollection)
async def read_ig_profiles_by_usernames(
    payload: ProfileUsernames,
    collection: Any = Depends(get_profiles_collection),
    _current_user: User = Depends(get_current_active_superuser),
) -> ProfileCollection:
    if not payload.usernames:
        raise HTTPException(status_code=400, detail="usernames cannot be empty")
    profiles = await get_profiles_by_usernames(collection, payload.usernames)
    return ProfileCollection(
        profiles=[Profile.model_validate(profile) for profile in profiles]
    )


@router.get("/", response_model=ProfileCollection)
async def read_ig_profiles(
    skip: int = 0,
    limit: int = 100,
    collection: Any = Depends(get_profiles_collection),
    _current_user: User = Depends(get_current_active_superuser),
) -> ProfileCollection:
    profiles = await list_profiles(collection, skip=skip, limit=limit)
    return ProfileCollection(
        profiles=[Profile.model_validate(profile) for profile in profiles]
    )


@router.get("/{profile_id}", response_model=Profile)
async def read_ig_profile(
    profile_id: str,
    collection: Any = Depends(get_profiles_collection),
    _current_user: User = Depends(get_current_active_superuser),
) -> Profile:
    return _require_profile(await get_profile(collection, profile_id))


@router.patch("/{profile_id}", response_model=Profile)
async def update_ig_profile(
    profile_id: str,
    patch: UpdateProfile,
    collection: Any = Depends(get_profiles_collection),
    _current_user: User = Depends(get_current_active_superuser),
) -> Profile:
    return _require_profile(await update_profile(collection, profile_id, patch))


@router.put("/{profile_id}", response_model=Profile)
async def replace_ig_profile(
    profile_id: str,
    profile_in: Profile,
    collection: Any = Depends(get_profiles_collection),
    _current_user: User = Depends(get_current_active_superuser),
) -> Profile:
    return _require_profile(await replace_profile(collection, profile_id, profile_in))


@router.delete("/{profile_id}", response_model=Profile)
async def delete_ig_profile(
    profile_id: str,
    collection: Any = Depends(get_profiles_collection),
    _current_user: User = Depends(get_current_active_superuser),
) -> Profile:
    return _require_profile(await delete_profile(collection, profile_id))


__all__ = ["router"]
