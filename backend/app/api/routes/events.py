from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.api.deps import CurrentUser
from app.features.user_events.service import (
    UserEventStreamService,
    UserEventsUnavailableError,
    get_user_event_stream_service,
)

router = APIRouter(prefix="/events", tags=["events"])


def get_stream_user_events_service(
    event_stream_service: Annotated[
        UserEventStreamService,
        Depends(get_user_event_stream_service),
    ],
) -> UserEventStreamService:
    try:
        event_stream_service.assert_available()
    except UserEventsUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return event_stream_service


@router.get("/stream", response_class=EventSourceResponse)
async def stream_user_events(
    request: Request,
    current_user: CurrentUser,
    event_stream_service: Annotated[
        UserEventStreamService,
        Depends(get_stream_user_events_service),
    ],
    last_event_id: Annotated[str | None, Header()] = None,
) -> AsyncIterator[ServerSentEvent]:
    async for event in event_stream_service.stream_events(
        request,
        user_id=str(current_user.id),
        last_event_id=last_event_id,
    ):
        yield event


__all__ = ["router", "stream_user_events"]
