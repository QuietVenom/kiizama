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
from app.schemas import Profile, ProfileCollection, UpdateProfile

router = APIRouter(prefix="/ig-profiles", tags=["ig-profiles"])


class ProfileUsernames(BaseModel):
    usernames: list[str]


@router.post("/", response_model=Profile, status_code=status.HTTP_201_CREATED)
async def create_ig_profile(
    profile: Profile,
    collection: Any = Depends(get_profiles_collection),
    _current_user=Depends(get_current_active_superuser),
) -> Profile:
    return await create_profile(collection, profile)


@router.get("/by-username/{username}", response_model=Profile)
async def read_ig_profile_by_username(
    username: str,
    _current_user: CurrentUser,
    collection: Any = Depends(get_profiles_collection),
) -> Profile:
    profile = await get_profile_by_username(collection, username)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/by-usernames", response_model=ProfileCollection)
async def read_ig_profiles_by_usernames(
    payload: ProfileUsernames,
    collection: Any = Depends(get_profiles_collection),
    _current_user=Depends(get_current_active_superuser),
) -> ProfileCollection:
    if not payload.usernames:
        raise HTTPException(status_code=400, detail="usernames cannot be empty")
    profiles = await get_profiles_by_usernames(collection, payload.usernames)
    return ProfileCollection(profiles=profiles)


@router.get("/", response_model=ProfileCollection)
async def read_ig_profiles(
    skip: int = 0,
    limit: int = 100,
    collection: Any = Depends(get_profiles_collection),
    _current_user=Depends(get_current_active_superuser),
) -> ProfileCollection:
    profiles = await list_profiles(collection, skip=skip, limit=limit)
    return ProfileCollection(profiles=profiles)


@router.get("/{profile_id}", response_model=Profile)
async def read_ig_profile(
    profile_id: str,
    collection: Any = Depends(get_profiles_collection),
    _current_user=Depends(get_current_active_superuser),
) -> Profile:
    profile = await get_profile(collection, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.patch("/{profile_id}", response_model=Profile)
async def update_ig_profile(
    profile_id: str,
    patch: UpdateProfile,
    collection: Any = Depends(get_profiles_collection),
    _current_user=Depends(get_current_active_superuser),
) -> Profile:
    profile = await update_profile(collection, profile_id, patch)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/{profile_id}", response_model=Profile)
async def replace_ig_profile(
    profile_id: str,
    profile_in: Profile,
    collection: Any = Depends(get_profiles_collection),
    _current_user=Depends(get_current_active_superuser),
) -> Profile:
    profile = await replace_profile(collection, profile_id, profile_in)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.delete("/{profile_id}", response_model=Profile)
async def delete_ig_profile(
    profile_id: str,
    collection: Any = Depends(get_profiles_collection),
    _current_user=Depends(get_current_active_superuser),
) -> Profile:
    profile = await delete_profile(collection, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


__all__ = ["router"]
