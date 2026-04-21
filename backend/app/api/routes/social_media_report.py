from __future__ import annotations

import io
import zipfile
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response

from app.api.deps import CurrentUser, SessionDep, get_profile_snapshots_collection
from app.features.billing import (
    FEATURE_ENDPOINT_KEYS,
    IDEMPOTENCY_HEADER_NAME,
    build_usage_request_key,
    finalize_usage_reservation,
    publish_billing_event,
    release_usage_reservation,
    reserve_feature_usage,
)
from app.features.rate_limit import POLICIES, rate_limit
from app.features.social_media_report.schemas import InstagramReportRequest
from app.features.social_media_report.service import (
    ReportFile,
    generate_instagram_report,
)

router = APIRouter(prefix="/social-media-report", tags=["social-media-report"])

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


@router.post(
    "/instagram",
    response_class=Response,
    responses=REPORT_FILE_RESPONSES,
    dependencies=[Depends(rate_limit(POLICIES.private_expensive))],
)
async def generate_instagram_report_endpoint(
    payload: InstagramReportRequest,
    current_user: CurrentUser,
    session: SessionDep,
    idempotency_key: Annotated[
        str | None, Header(alias=IDEMPOTENCY_HEADER_NAME)
    ] = None,
    collection: Any = Depends(get_profile_snapshots_collection),
) -> Response:
    request_key = build_usage_request_key(
        user_id=current_user.id,
        request_scope="social-media-report",
        idempotency_key=idempotency_key,
    )
    reserve_feature_usage(
        session=session,
        user_id=current_user.id,
        feature_code="social_media_report",
        endpoint_key=FEATURE_ENDPOINT_KEYS["social_media_report"],
        max_units_requested=len(payload.usernames),
        request_key=request_key,
        metadata={"usernames": payload.usernames},
    )
    try:
        files = await generate_instagram_report(collection, payload)
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
        quantity_consumed=len(payload.usernames),
        metadata={"generated_files": len(files)},
    )
    await publish_billing_event(
        session=session,
        user_id=current_user.id,
        event_name="account.usage.updated",
    )

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
        headers={"Content-Disposition": 'attachment; filename="instagram_reports.zip"'},
    )


def _build_zip(files: list[ReportFile]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for file in files:
            zip_file.writestr(file.filename, file.content)
    return buffer.getvalue()


__all__ = ["router"]
