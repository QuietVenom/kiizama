from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_active_superuser, get_profile_snapshots_collection
from app.crud.profile_snapshots import (
    create_profile_snapshot,
    delete_profile_snapshot,
    get_profile_snapshot,
    list_profile_snapshots,
    list_profile_snapshots_full,
    replace_profile_snapshot,
    update_profile_snapshot,
)
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
    dependencies=[Depends(get_current_active_superuser)],
)

Document = dict[str, Any]


def _require_snapshot(snapshot_doc: Document | None) -> ProfileSnapshot:
    if not snapshot_doc:
        raise HTTPException(status_code=404, detail="Profile snapshot not found")
    return ProfileSnapshot.model_validate(snapshot_doc)


@router.post("/", response_model=ProfileSnapshot, status_code=status.HTTP_201_CREATED)
async def create_ig_profile_snapshot(
    snapshot: ProfileSnapshot,
    collection: Any = Depends(get_profile_snapshots_collection),
) -> ProfileSnapshot:
    created = await create_profile_snapshot(collection, snapshot)
    return _require_snapshot(created)


@router.get("/", response_model=ProfileSnapshotCollection)
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


@router.get("/advanced", response_model=ProfileSnapshotExpandedCollection)
async def read_ig_profile_snapshots_advanced(
    skip: int = 0,
    limit: int = 100,
    usernames: list[str] | None = Query(default=None),
    collection: Any = Depends(get_profile_snapshots_collection),
) -> ProfileSnapshotExpandedCollection:
    snapshots = await list_profile_snapshots_full(
        collection,
        skip=skip,
        limit=limit,
        usernames=usernames,
    )
    return ProfileSnapshotExpandedCollection(
        snapshots=[
            ProfileSnapshotExpanded.model_validate(snapshot) for snapshot in snapshots
        ]
    )


@router.get("/{snapshot_id}", response_model=ProfileSnapshot)
async def read_ig_profile_snapshot(
    snapshot_id: str, collection: Any = Depends(get_profile_snapshots_collection)
) -> ProfileSnapshot:
    return _require_snapshot(await get_profile_snapshot(collection, snapshot_id))


@router.patch("/{snapshot_id}", response_model=ProfileSnapshot)
async def update_ig_profile_snapshot(
    snapshot_id: str,
    patch: UpdateProfileSnapshot,
    collection: Any = Depends(get_profile_snapshots_collection),
) -> ProfileSnapshot:
    return _require_snapshot(
        await update_profile_snapshot(collection, snapshot_id, patch)
    )


@router.put("/{snapshot_id}", response_model=ProfileSnapshot)
async def replace_ig_profile_snapshot(
    snapshot_id: str,
    snapshot_in: ProfileSnapshot,
    collection: Any = Depends(get_profile_snapshots_collection),
) -> ProfileSnapshot:
    return _require_snapshot(
        await replace_profile_snapshot(collection, snapshot_id, snapshot_in)
    )


@router.delete("/{snapshot_id}", response_model=ProfileSnapshot)
async def delete_ig_profile_snapshot(
    snapshot_id: str, collection: Any = Depends(get_profile_snapshots_collection)
) -> ProfileSnapshot:
    return _require_snapshot(await delete_profile_snapshot(collection, snapshot_id))


__all__ = ["router"]
