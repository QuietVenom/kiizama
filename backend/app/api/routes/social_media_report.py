from __future__ import annotations

import io
import zipfile
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.deps import CurrentUser, get_profile_snapshots_collection
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
    _current_user: CurrentUser,
    collection: Any = Depends(get_profile_snapshots_collection),
) -> Response:
    try:
        files = await generate_instagram_report(collection, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

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
