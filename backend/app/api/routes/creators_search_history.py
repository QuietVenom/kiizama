from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser
from app.features.creators_search_history import (
    CreatorsSearchHistoryCreateRequest,
    CreatorsSearchHistoryItem,
    CreatorsSearchHistoryListResponse,
    CreatorsSearchHistoryServiceDep,
    CreatorsSearchHistoryUnavailableError,
)

router = APIRouter(
    prefix="/creators-search/history",
    tags=["creators-search-history"],
)


@router.get("", response_model=CreatorsSearchHistoryListResponse)
async def list_creators_search_history(
    current_user: CurrentUser,
    service: CreatorsSearchHistoryServiceDep,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> CreatorsSearchHistoryListResponse:
    try:
        return await service.list_history(
            user_id=str(current_user.id),
            limit=limit,
        )
    except CreatorsSearchHistoryUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("", response_model=CreatorsSearchHistoryItem)
async def create_creators_search_history_entry(
    payload: CreatorsSearchHistoryCreateRequest,
    current_user: CurrentUser,
    service: CreatorsSearchHistoryServiceDep,
) -> CreatorsSearchHistoryItem:
    try:
        return await service.create_entry(
            user_id=str(current_user.id),
            payload=payload,
        )
    except CreatorsSearchHistoryUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


__all__ = ["router"]
