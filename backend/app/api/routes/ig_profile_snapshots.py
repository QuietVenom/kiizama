import asyncio
import logging
from collections.abc import Awaitable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    get_current_active_superuser,
    get_current_user,
    get_profile_snapshots_collection,
)
from app.crud.profile_snapshots import (
    create_profile_snapshot,
    delete_profile_snapshot,
    get_profile_snapshot,
    list_profile_snapshots,
    list_profile_snapshots_full,
    replace_profile_snapshot,
    update_profile_snapshot,
)
from app.features.general.types import (
    is_allowed_profile_picture_url,
    resolve_profile_picture_data_uri,
)
from app.features.ig_scrapper.utils import should_refresh_profile
from app.schemas import (
    ProfileSnapshot,
    ProfileSnapshotCollection,
    ProfileSnapshotExpanded,
    ProfileSnapshotExpandedCollection,
    UpdateProfileSnapshot,
)

router = APIRouter(
    prefix="/ig-profile-snapshots",
    tags=["ig-profile-snapshots"],
)

Document = dict[str, Any]
logger = logging.getLogger(__name__)


def _require_snapshot(snapshot_doc: Document | None) -> ProfileSnapshot:
    if not snapshot_doc:
        raise HTTPException(status_code=404, detail="Profile snapshot not found")
    return ProfileSnapshot.model_validate(snapshot_doc)


def _resolve_missing_usernames(
    usernames: list[str] | None, snapshots: list[Document]
) -> list[str]:
    if not usernames:
        return []

    resolved_usernames = _resolve_snapshot_profiles_by_username(snapshots)
    return list(
        dict.fromkeys(
            username for username in usernames if username not in resolved_usernames
        )
    )


def _resolve_expired_usernames(
    usernames: list[str] | None, snapshots: list[Document]
) -> list[str]:
    if not usernames:
        return []

    resolved_profiles = _resolve_snapshot_profiles_by_username(snapshots)
    return list(
        dict.fromkeys(
            username
            for username in usernames
            if username in resolved_profiles
            and should_refresh_profile(resolved_profiles[username])
        )
    )


def _resolve_snapshot_profiles_by_username(
    snapshots: list[Document],
) -> dict[str, Document]:
    resolved_profiles: dict[str, Document] = {}
    for snapshot in snapshots:
        profile = snapshot.get("profile")
        if not isinstance(profile, dict):
            continue
        profile_username = profile.get("username")
        if isinstance(profile_username, str):
            resolved_profiles.setdefault(profile_username, profile)
    return resolved_profiles


async def _enrich_snapshot_profile_picture_sources(snapshots: list[Document]) -> None:
    profiles_to_enrich: list[Document] = []
    tasks: list[Awaitable[str | None]] = []

    for snapshot in snapshots:
        profile = snapshot.get("profile")
        if not isinstance(profile, dict):
            continue

        profile_pic_url = profile.get("profile_pic_url")
        if (
            not isinstance(profile_pic_url, str)
            or not profile_pic_url
            or not is_allowed_profile_picture_url(profile_pic_url)
        ):
            continue

        profiles_to_enrich.append(profile)
        tasks.append(
            asyncio.to_thread(
                resolve_profile_picture_data_uri,
                profile_pic_url,
                logger,
            )
        )

    if not tasks:
        return

    resolved_sources = await asyncio.gather(*tasks)
    for profile, resolved_source in zip(
        profiles_to_enrich, resolved_sources, strict=False
    ):
        if isinstance(resolved_source, str) and resolved_source:
            profile["profile_pic_src"] = resolved_source


@router.post(
    "/",
    response_model=ProfileSnapshot,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_active_superuser)],
)
async def create_ig_profile_snapshot(
    snapshot: ProfileSnapshot,
    collection: Any = Depends(get_profile_snapshots_collection),
) -> ProfileSnapshot:
    created = await create_profile_snapshot(collection, snapshot)
    return _require_snapshot(created)


@router.get(
    "/",
    response_model=ProfileSnapshotCollection,
    dependencies=[Depends(get_current_active_superuser)],
)
async def read_ig_profile_snapshots(
    skip: int = 0,
    limit: int = 100,
    snapshot_ids: list[str] | None = Query(default=None),
    collection: Any = Depends(get_profile_snapshots_collection),
) -> ProfileSnapshotCollection:
    snapshots = await list_profile_snapshots(
        collection,
        skip=skip,
        limit=limit,
        snapshot_ids=snapshot_ids,
    )
    return ProfileSnapshotCollection(
        snapshots=[ProfileSnapshot.model_validate(snapshot) for snapshot in snapshots]
    )


@router.get(
    "/advanced",
    response_model=ProfileSnapshotExpandedCollection,
    dependencies=[Depends(get_current_user)],
)
async def read_ig_profile_snapshots_advanced(
    skip: int = 0,
    limit: int = 100,
    usernames: Annotated[list[str] | None, Query(max_length=50)] = None,
    collection: Any = Depends(get_profile_snapshots_collection),
) -> ProfileSnapshotExpandedCollection:
    snapshots = await list_profile_snapshots_full(
        collection,
        skip=skip,
        limit=limit,
        usernames=usernames,
    )
    await _enrich_snapshot_profile_picture_sources(snapshots)
    return ProfileSnapshotExpandedCollection(
        missing_usernames=_resolve_missing_usernames(usernames, snapshots),
        expired_usernames=_resolve_expired_usernames(usernames, snapshots),
        snapshots=[
            ProfileSnapshotExpanded.model_validate(snapshot) for snapshot in snapshots
        ],
    )


@router.get(
    "/{snapshot_id}",
    response_model=ProfileSnapshot,
    dependencies=[Depends(get_current_active_superuser)],
)
async def read_ig_profile_snapshot(
    snapshot_id: str, collection: Any = Depends(get_profile_snapshots_collection)
) -> ProfileSnapshot:
    return _require_snapshot(await get_profile_snapshot(collection, snapshot_id))


@router.patch(
    "/{snapshot_id}",
    response_model=ProfileSnapshot,
    dependencies=[Depends(get_current_active_superuser)],
)
async def update_ig_profile_snapshot(
    snapshot_id: str,
    patch: UpdateProfileSnapshot,
    collection: Any = Depends(get_profile_snapshots_collection),
) -> ProfileSnapshot:
    return _require_snapshot(
        await update_profile_snapshot(collection, snapshot_id, patch)
    )


@router.put(
    "/{snapshot_id}",
    response_model=ProfileSnapshot,
    dependencies=[Depends(get_current_active_superuser)],
)
async def replace_ig_profile_snapshot(
    snapshot_id: str,
    snapshot_in: ProfileSnapshot,
    collection: Any = Depends(get_profile_snapshots_collection),
) -> ProfileSnapshot:
    return _require_snapshot(
        await replace_profile_snapshot(collection, snapshot_id, snapshot_in)
    )


@router.delete(
    "/{snapshot_id}",
    response_model=ProfileSnapshot,
    dependencies=[Depends(get_current_active_superuser)],
)
async def delete_ig_profile_snapshot(
    snapshot_id: str, collection: Any = Depends(get_profile_snapshots_collection)
) -> ProfileSnapshot:
    return _require_snapshot(await delete_profile_snapshot(collection, snapshot_id))


__all__ = ["router"]
