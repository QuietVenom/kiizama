from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.api.deps import CurrentUserId
from app.features.rate_limit import POLICIES, rate_limit
from app.features.user_events.service import (
    UserEventStreamService,
    get_user_event_stream_service,
)

router = APIRouter(prefix="/events", tags=["events"])


async def get_stream_user_events_service(
    event_stream_service: Annotated[
        UserEventStreamService,
        Depends(get_user_event_stream_service),
    ],
) -> UserEventStreamService:
    await event_stream_service.assert_connection_available()
    return event_stream_service


@router.get(
    "/stream",
    response_class=EventSourceResponse,
    dependencies=[Depends(rate_limit(POLICIES.stream_connect))],
)
async def stream_user_events(
    request: Request,
    current_user_id: CurrentUserId,
    event_stream_service: Annotated[
        UserEventStreamService,
        Depends(get_stream_user_events_service),
    ],
    last_event_id: Annotated[str | None, Header()] = None,
) -> AsyncIterator[ServerSentEvent]:
    async for event in event_stream_service.stream_events(
        request,
        user_id=current_user_id,
        last_event_id=last_event_id,
    ):
        yield event


__all__ = ["router", "stream_user_events"]
