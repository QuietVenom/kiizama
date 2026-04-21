from __future__ import annotations

import io
import zipfile
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response

from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_profile_snapshots_collection,
    get_profiles_collection,
)
from app.features.billing import (
    FEATURE_ENDPOINT_KEYS,
    IDEMPOTENCY_HEADER_NAME,
    build_usage_request_key,
    finalize_usage_reservation,
    publish_billing_event,
    release_usage_reservation,
    reserve_feature_usage,
)
from app.features.brand_intelligence.schemas import (
    ProfileExistenceCollection,
    ReputationCampaignStrategyRequest,
    ReputationCreatorStrategyRequest,
)
from app.features.brand_intelligence.service import (
    ReportFile,
    check_profile_usernames_existence,
    generate_reputation_campaign_strategy_report,
    generate_reputation_creator_strategy_report,
)
from app.features.rate_limit import POLICIES, rate_limit

router = APIRouter(prefix="/brand-intelligence", tags=["brand-intelligence"])

REPORT_FILE_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "Generated report file",
        "content": {
            "text/html": {},
            "application/pdf": {},
            "application/zip": {},
        },
    }
}


@router.get(
    "/profiles-existence",
    response_model=ProfileExistenceCollection,
    dependencies=[Depends(rate_limit(POLICIES.private_expensive))],
)
async def read_profiles_existence(
    _current_user: CurrentUser,
    usernames: Annotated[list[str] | None, Query()] = None,
    profiles_collection: Any = Depends(get_profiles_collection),
) -> ProfileExistenceCollection:
    try:
        return await check_profile_usernames_existence(
            usernames,
            profiles_collection=profiles_collection,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/reputation-campaign-strategy",
    response_class=Response,
    responses=REPORT_FILE_RESPONSES,
    dependencies=[Depends(rate_limit(POLICIES.private_expensive))],
)
async def generate_reputation_campaign_strategy_endpoint(
    payload: ReputationCampaignStrategyRequest,
    current_user: CurrentUser,
    session: SessionDep,
    idempotency_key: Annotated[
        str | None, Header(alias=IDEMPOTENCY_HEADER_NAME)
    ] = None,
    profiles_collection: Any = Depends(get_profiles_collection),
    profile_snapshots_collection: Any = Depends(get_profile_snapshots_collection),
) -> Response:
    files = await _execute_report_generation(
        generator=generate_reputation_campaign_strategy_report,
        payload=payload,
        current_user=current_user,
        session=session,
        endpoint_key=FEATURE_ENDPOINT_KEYS["reputation_strategy.campaign"],
        idempotency_key=idempotency_key,
        profiles_collection=profiles_collection,
        profile_snapshots_collection=profile_snapshots_collection,
    )
    return _build_files_response(
        files,
        zip_filename="reputation_campaign_strategy_reports.zip",
    )


@router.post(
    "/reputation-creator-strategy",
    response_class=Response,
    responses=REPORT_FILE_RESPONSES,
    dependencies=[Depends(rate_limit(POLICIES.private_expensive))],
)
async def generate_reputation_creator_strategy_endpoint(
    payload: ReputationCreatorStrategyRequest,
    current_user: CurrentUser,
    session: SessionDep,
    idempotency_key: Annotated[
        str | None, Header(alias=IDEMPOTENCY_HEADER_NAME)
    ] = None,
    profiles_collection: Any = Depends(get_profiles_collection),
    profile_snapshots_collection: Any = Depends(get_profile_snapshots_collection),
) -> Response:
    files = await _execute_report_generation(
        generator=generate_reputation_creator_strategy_report,
        payload=payload,
        current_user=current_user,
        session=session,
        endpoint_key=FEATURE_ENDPOINT_KEYS["reputation_strategy.creator"],
        idempotency_key=idempotency_key,
        profiles_collection=profiles_collection,
        profile_snapshots_collection=profile_snapshots_collection,
    )
    return _build_files_response(
        files,
        zip_filename="reputation_creator_strategy_reports.zip",
    )


async def _execute_report_generation(
    *,
    generator: Callable[..., Awaitable[list[ReportFile]]],
    payload: Any,
    current_user: CurrentUser,
    session: SessionDep,
    endpoint_key: str,
    idempotency_key: str | None,
    profiles_collection: Any,
    profile_snapshots_collection: Any,
) -> list[ReportFile]:
    request_key = build_usage_request_key(
        user_id=current_user.id,
        request_scope=endpoint_key,
        idempotency_key=idempotency_key,
    )
    reserve_feature_usage(
        session=session,
        user_id=current_user.id,
        feature_code="reputation_strategy",
        endpoint_key=endpoint_key,
        max_units_requested=1,
        request_key=request_key,
    )
    try:
        files = await generator(
            profiles_collection=profiles_collection,
            profile_snapshots_collection=profile_snapshots_collection,
            payload=payload,
        )
    except LookupError as exc:
        release_usage_reservation(
            session=session,
            request_key=request_key,
            metadata={"error": str(exc)},
        )
        await publish_billing_event(
            session=session,
            user_id=current_user.id,
            event_name="account.usage.updated",
        )
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        release_usage_reservation(
            session=session,
            request_key=request_key,
            metadata={"error": str(exc)},
        )
        await publish_billing_event(
            session=session,
            user_id=current_user.id,
            event_name="account.usage.updated",
        )
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        release_usage_reservation(session=session, request_key=request_key)
        await publish_billing_event(
            session=session,
            user_id=current_user.id,
            event_name="account.usage.updated",
        )
        raise

    finalize_usage_reservation(
        session=session,
        request_key=request_key,
        quantity_consumed=1,
        metadata={"generated_files": len(files)},
    )
    await publish_billing_event(
        session=session,
        user_id=current_user.id,
        event_name="account.usage.updated",
    )
    return files


def _build_files_response(files: list[ReportFile], *, zip_filename: str) -> Response:
    if len(files) == 1:
        file = files[0]
        return Response(
            content=file.content,
            media_type=file.content_type,
            headers={"Content-Disposition": f'attachment; filename="{file.filename}"'},
        )

    zip_bytes = _build_zip(files)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )


def _build_zip(files: list[ReportFile]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for file in files:
            zip_file.writestr(file.filename, file.content)
    return buffer.getvalue()


__all__ = ["router"]
