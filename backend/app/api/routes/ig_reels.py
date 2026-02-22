from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_active_superuser, get_reels_collection
from app.crud.reels import (
    create_reel,
    delete_reel,
    get_reel,
    list_reels,
    replace_reel,
    update_reel,
)
from app.schemas import Reel, ReelCollection, UpdateReel

router = APIRouter(
    prefix="/ig-reels",
    tags=["ig-reels"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.post("/", response_model=Reel, status_code=status.HTTP_201_CREATED)
async def create_ig_reel(
    reel: Reel, collection: Any = Depends(get_reels_collection)
) -> Reel:
    return await create_reel(collection, reel)


@router.get("/", response_model=ReelCollection)
async def read_ig_reels(
    skip: int = 0,
    limit: int = 100,
    collection: Any = Depends(get_reels_collection),
) -> ReelCollection:
    reels = await list_reels(collection, skip=skip, limit=limit)
    return ReelCollection(reels=reels)


@router.get("/{reel_id}", response_model=Reel)
async def read_ig_reel(
    reel_id: str, collection: Any = Depends(get_reels_collection)
) -> Reel:
    reel = await get_reel(collection, reel_id)
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    return reel


@router.patch("/{reel_id}", response_model=Reel)
async def update_ig_reel(
    reel_id: str,
    patch: UpdateReel,
    collection: Any = Depends(get_reels_collection),
) -> Reel:
    reel = await update_reel(collection, reel_id, patch)
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    return reel


@router.put("/{reel_id}", response_model=Reel)
async def replace_ig_reel(
    reel_id: str,
    reel_in: Reel,
    collection: Any = Depends(get_reels_collection),
) -> Reel:
    reel = await replace_reel(collection, reel_id, reel_in)
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    return reel


@router.delete("/{reel_id}", response_model=Reel)
async def delete_ig_reel(
    reel_id: str, collection: Any = Depends(get_reels_collection)
) -> Reel:
    reel = await delete_reel(collection, reel_id)
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    return reel


__all__ = ["router"]
