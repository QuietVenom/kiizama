from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UserEventEnvelope(BaseModel):
    topic: str = Field(min_length=1)
    source: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    notification_id: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class UserStreamEntry(BaseModel):
    event_id: str
    event_name: str
    notification_id: str | None = None
    envelope_json: str


__all__ = ["UserEventEnvelope", "UserStreamEntry"]
