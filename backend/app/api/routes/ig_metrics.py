from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_active_superuser, get_metrics_collection
from app.crud.metrics import (
    create_metrics,
    delete_metrics,
    get_metrics,
    list_metrics,
    replace_metrics,
    update_metrics,
)
from app.schemas import Metrics, MetricsCollection, UpdateMetrics

router = APIRouter(
    prefix="/ig-metrics",
    tags=["ig-metrics"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.post("/", response_model=Metrics, status_code=status.HTTP_201_CREATED)
async def create_ig_metrics(
    metrics: Metrics, collection: Any = Depends(get_metrics_collection)
) -> Metrics:
    return await create_metrics(collection, metrics)


@router.get("/", response_model=MetricsCollection)
async def read_ig_metrics(
    skip: int = 0,
    limit: int = 100,
    collection: Any = Depends(get_metrics_collection),
) -> MetricsCollection:
    metrics = await list_metrics(collection, skip=skip, limit=limit)
    return MetricsCollection(metrics=metrics)


@router.get("/{metrics_id}", response_model=Metrics)
async def read_ig_metrics_by_id(
    metrics_id: str, collection: Any = Depends(get_metrics_collection)
) -> Metrics:
    metrics = await get_metrics(collection, metrics_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Metrics not found")
    return metrics


@router.patch("/{metrics_id}", response_model=Metrics)
async def update_ig_metrics(
    metrics_id: str,
    patch: UpdateMetrics,
    collection: Any = Depends(get_metrics_collection),
) -> Metrics:
    metrics = await update_metrics(collection, metrics_id, patch)
    if not metrics:
        raise HTTPException(status_code=404, detail="Metrics not found")
    return metrics


@router.put("/{metrics_id}", response_model=Metrics)
async def replace_ig_metrics(
    metrics_id: str,
    metrics_in: Metrics,
    collection: Any = Depends(get_metrics_collection),
) -> Metrics:
    metrics = await replace_metrics(collection, metrics_id, metrics_in)
    if not metrics:
        raise HTTPException(status_code=404, detail="Metrics not found")
    return metrics


@router.delete("/{metrics_id}", response_model=Metrics)
async def delete_ig_metrics(
    metrics_id: str, collection: Any = Depends(get_metrics_collection)
) -> Metrics:
    metrics = await delete_metrics(collection, metrics_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Metrics not found")
    return metrics


__all__ = ["router"]
