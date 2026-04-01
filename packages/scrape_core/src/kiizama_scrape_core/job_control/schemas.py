from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

JobExecutionMode = Literal["worker", "apify"]
JobStatus = Literal["queued", "running", "done", "failed"]


class JobQueueSpec(BaseModel):
    domain: str = Field(min_length=1)
    execution_mode: JobExecutionMode = "worker"
    state_ttl_seconds: int = Field(gt=0)
    queue_maxlen: int = Field(gt=0)

    model_config = ConfigDict(frozen=True)

    @property
    def queue_key(self) -> str:
        from .keys import build_queue_key

        return build_queue_key(self)

    @property
    def consumer_group(self) -> str:
        from .keys import build_consumer_group

        return build_consumer_group(self)


class QueuedJobMessage(BaseModel):
    job_id: str = Field(min_length=1)
    owner_user_id: str = Field(min_length=1)
    created_at: datetime
    execution_mode: JobExecutionMode = "worker"
    expires_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    message_id: str | None = None


class JobTransientState(BaseModel):
    status: JobStatus
    attempts: int = Field(default=0, ge=0)
    worker_id: str | None = None
    started_at: datetime | None = None
    heartbeat_at: datetime | None = None
    leased_until: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    expires_at: datetime | None = None
    error: str | None = None
    notification_id: str | None = None
    terminal_event_id: str | None = None


TerminalizationDecisionStatus = Literal[
    "accepted_new",
    "accepted_pending",
    "duplicate",
    "conflict",
]


class TerminalizationDecision(BaseModel):
    decision: TerminalizationDecisionStatus
    status: Literal["done", "failed"]
    attempts: int = Field(default=0, ge=0)
    worker_id: str | None = None
    completed_at: datetime | None = None
    notification_id: str | None = None
    terminal_event_id: str | None = None


class JobLeaseStatus(BaseModel):
    job_id: str = Field(min_length=1)
    lease_token: str = Field(min_length=1)
    owned: bool
    leased_until: datetime | None = None


__all__ = [
    "JobExecutionMode",
    "JobLeaseStatus",
    "JobQueueSpec",
    "JobStatus",
    "JobTransientState",
    "QueuedJobMessage",
    "TerminalizationDecision",
    "TerminalizationDecisionStatus",
]
