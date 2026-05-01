from __future__ import annotations

import logging
import uuid

from sqlmodel import Session

from app.features.user_events.repository import get_user_events_repository
from app.features.user_events.schemas import UserEventEnvelope

from ..constants import ACCOUNT_KIND, ACCOUNT_SOURCE, ACCOUNT_TOPIC
from ..models import utcnow
from . import access_read as access_read_service

logger = logging.getLogger(__name__)


async def publish_billing_event(
    *,
    session: Session,
    user_id: uuid.UUID,
    event_name: str,
) -> None:
    try:
        summary = access_read_service.build_billing_summary(
            session=session,
            user_id=user_id,
            utcnow_fn=utcnow,
        )
        repository = get_user_events_repository()
        await repository.publish_event(
            user_id=str(user_id),
            event_name=event_name,
            envelope=UserEventEnvelope(
                topic=ACCOUNT_TOPIC,
                source=ACCOUNT_SOURCE,
                kind=ACCOUNT_KIND,
                notification_id=f"{event_name}:{user_id}:{uuid.uuid4()}",
                payload=summary.model_dump(mode="json"),
            ),
        )
    except Exception:
        logger.exception(
            "Failed to publish billing SSE event",
            extra={"user_id": str(user_id), "event_name": event_name},
        )


__all__ = ["publish_billing_event"]
