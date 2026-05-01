from __future__ import annotations

import logging
import uuid

from sqlmodel import Session

from app.features.billing.services.cleanup import delete_user_billing_state
from app.features.user_events.repository import (
    UserEventsUnavailableError,
    get_user_events_repository,
)

from ..repository import (
    build_user_related_cleanup_context,
    delete_user_related_cleanup_context,
)

logger = logging.getLogger(__name__)


async def cleanup_user_related_data_before_delete(
    *,
    session: Session,
    user_id: uuid.UUID,
) -> None:
    context = build_user_related_cleanup_context(session=session, user_id=user_id)
    await delete_user_billing_state(session=session, user_id=user_id)
    delete_user_related_cleanup_context(session=session, context=context)


async def delete_user_event_stream_best_effort(*, user_id: uuid.UUID) -> None:
    try:
        await get_user_events_repository().delete_user_stream(user_id=str(user_id))
    except (UserEventsUnavailableError, RuntimeError):
        logger.exception(
            "Failed to delete user event stream during account cleanup.",
            extra={"user_id": str(user_id)},
        )


__all__ = [
    "cleanup_user_related_data_before_delete",
    "delete_user_event_stream_best_effort",
]
